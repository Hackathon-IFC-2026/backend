import smtplib
from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Board, Task, TaskInvitation, User


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='kando.gerenciador@gmail.com',
    FRONTEND_BASE_URL='https://kando.test',
)
class TaskInvitationAPITests(APITestCase):
    boards_url = '/api/boards/'
    tasks_url = '/api/tasks/'
    invitations_url = '/api/invitations/'
    pending_invitations_url = '/api/invitations/pending/'
    inviter_password = 'InviterPassword!123'
    invitee_password = 'InviteePassword!123'
    other_password = 'OtherPassword!123'
    task_title = 'Prepare launch'
    board_title = 'Product'

    def setUp(self):
        cache.clear()
        self.inviter = User.objects.create_user(
            'inviter@example.com',
            self.inviter_password,
            name='Alex Inviter',
        )
        self.invitee = User.objects.create_user('invitee@example.com', self.invitee_password)
        self.other_user = User.objects.create_user('other@example.com', self.other_password)
        self.board = Board.objects.create(owner=self.inviter, title=self.board_title)
        self.task = Task.objects.create(
            board=self.board,
            title=self.task_title,
            created_by=self.inviter,
        )

    def invite(self, email=None):
        return self.client.post(
            self.invitations_url,
            {'task': self.task.pk, 'email': email or self.invitee.email},
            format='json',
        )

    def test_invite_sends_html_and_text_to_registered_user_without_adding_them(self):
        self.client.force_authenticate(self.inviter)

        response = self.invite()

        assert response.status_code == status.HTTP_201_CREATED
        invitation = TaskInvitation.objects.get()
        assert invitation.status == TaskInvitation.Status.PENDING
        assert invitation.invited_by == self.inviter
        assert invitation.invitee == self.invitee
        assert not self.task.participants.filter(pk=self.invitee.pk).exists()
        assert len(mail.outbox) == 1
        message = mail.outbox[0]
        assert message.from_email == 'kando.gerenciador@gmail.com'
        assert message.to == [self.invitee.email]
        assert self.task_title in message.body
        assert self.board_title in message.body
        assert 'Alex Inviter' in message.body
        assert len(message.alternatives) == 1
        html_body = message.alternatives[0][0]
        assert message.alternatives[0][1] == 'text/html'
        assert '#1A3721' in html_body
        assert 'Aceitar convite' in html_body
        assert 'Recusar convite' in html_body
        assert f'https://kando.test/convites/{invitation.pk}/aceitar' in html_body
        assert f'https://kando.test/convites/{invitation.pk}/recusar' in html_body
        assert response.data['status'] == TaskInvitation.Status.PENDING

    def test_authenticated_user_can_create_and_list_owned_boards_and_tasks(self):
        self.client.force_authenticate(self.inviter)
        board_response = self.client.post(
            self.boards_url,
            {'title': 'Personal', 'description': 'My work'},
            format='json',
        )

        assert board_response.status_code == status.HTTP_201_CREATED
        assert board_response.data['owner'] == self.inviter.pk

        task_response = self.client.post(
            self.tasks_url,
            {'board': board_response.data['id'], 'title': 'Review', 'description': 'Review the plan'},
            format='json',
        )

        assert task_response.status_code == status.HTTP_201_CREATED
        assert task_response.data['created_by'] == self.inviter.pk
        assert task_response.data['status'] == Task.Status.TODO
        assert self.client.get(self.boards_url).status_code == status.HTTP_200_OK
        assert self.client.get(self.tasks_url).status_code == status.HTTP_200_OK

        self.client.force_authenticate(self.other_user)
        assert self.client.get(self.boards_url).data['results'] == []
        assert self.client.get(self.tasks_url).data['results'] == []

    def test_only_task_creator_or_board_owner_can_invite(self):
        self.client.force_authenticate(self.other_user)

        response = self.invite()

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not TaskInvitation.objects.exists()
        assert mail.outbox == []

    def test_nonexistent_and_inactive_recipients_are_rejected(self):
        self.client.force_authenticate(self.inviter)
        inactive = User.objects.create_user(
            'inactive@example.com',
            'InactivePassword!123',
            is_active=False,
        )

        for recipient in ('missing@example.com', inactive.email):
            response = self.invite(recipient)
            assert response.status_code == status.HTTP_400_BAD_REQUEST

        assert not TaskInvitation.objects.exists()
        assert mail.outbox == []

    def test_pending_duplicate_is_rejected(self):
        self.client.force_authenticate(self.inviter)

        first_response = self.invite()
        second_response = self.invite()

        assert first_response.status_code == status.HTTP_201_CREATED
        assert second_response.status_code == status.HTTP_409_CONFLICT
        assert TaskInvitation.objects.count() == 1
        assert len(mail.outbox) == 1

    def test_pending_list_contains_only_authenticated_users_own_invites(self):
        self.client.force_authenticate(self.inviter)
        self.invite()
        invitation = TaskInvitation.objects.get()

        self.client.force_authenticate(self.invitee)
        response = self.client.get(self.pending_invitations_url)

        assert response.status_code == status.HTTP_200_OK
        assert [item['id'] for item in response.data['results']] == [str(invitation.pk)]

        self.client.force_authenticate(self.other_user)
        response = self.client.get(self.pending_invitations_url)
        assert response.data['results'] == []

    def test_opening_action_link_does_not_change_invitation(self):
        self.client.force_authenticate(self.inviter)
        self.invite()
        invitation = TaskInvitation.objects.get()
        self.client.force_authenticate(self.invitee)

        response = self.client.get(f'{self.invitations_url}{invitation.pk}/accept/')

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        invitation.refresh_from_db()
        assert invitation.status == TaskInvitation.Status.PENDING
        assert not self.task.participants.filter(pk=self.invitee.pk).exists()

    def test_only_invitee_can_accept_and_participation_starts_on_acceptance(self):
        self.client.force_authenticate(self.inviter)
        self.invite()
        invitation = TaskInvitation.objects.get()

        self.client.force_authenticate(self.other_user)
        wrong_user_response = self.client.post(f'{self.invitations_url}{invitation.pk}/accept/')
        assert wrong_user_response.status_code == status.HTTP_404_NOT_FOUND
        invitation.refresh_from_db()
        assert invitation.status == TaskInvitation.Status.PENDING
        assert not self.task.participants.filter(pk=self.invitee.pk).exists()

        self.client.force_authenticate(self.invitee)
        response = self.client.post(f'{self.invitations_url}{invitation.pk}/accept/')

        assert response.status_code == status.HTTP_200_OK
        invitation.refresh_from_db()
        assert invitation.status == TaskInvitation.Status.ACCEPTED
        assert invitation.responded_at is not None
        assert self.task.participants.filter(pk=self.invitee.pk).exists()

        repeated_response = self.client.post(f'{self.invitations_url}{invitation.pk}/accept/')
        assert repeated_response.status_code == status.HTTP_409_CONFLICT
        assert self.task.participants.filter(pk=self.invitee.pk).count() == 1

    def test_decline_does_not_add_participant_and_cannot_be_reused(self):
        self.client.force_authenticate(self.inviter)
        self.invite()
        invitation = TaskInvitation.objects.get()
        self.client.force_authenticate(self.invitee)

        response = self.client.post(f'{self.invitations_url}{invitation.pk}/decline/')

        assert response.status_code == status.HTTP_200_OK
        invitation.refresh_from_db()
        assert invitation.status == TaskInvitation.Status.DECLINED
        assert invitation.responded_at is not None
        assert not self.task.participants.filter(pk=self.invitee.pk).exists()
        assert self.client.post(f'{self.invitations_url}{invitation.pk}/accept/').status_code == (
            status.HTTP_409_CONFLICT
        )

    def test_expired_invitation_cannot_be_accepted(self):
        self.client.force_authenticate(self.inviter)
        self.invite()
        invitation = TaskInvitation.objects.get()
        invitation.expires_at = timezone.now() - timedelta(seconds=1)
        invitation.save(update_fields=('expires_at',))
        self.client.force_authenticate(self.invitee)

        response = self.client.post(f'{self.invitations_url}{invitation.pk}/accept/')

        assert response.status_code == status.HTTP_410_GONE
        invitation.refresh_from_db()
        assert invitation.status == TaskInvitation.Status.EXPIRED
        assert not self.task.participants.filter(pk=self.invitee.pk).exists()

    def test_smtp_failure_rolls_back_invitation(self):
        self.client.force_authenticate(self.inviter)
        with patch(
            'core.services.task_invitations.EmailMultiAlternatives.send',
            side_effect=smtplib.SMTPServerDisconnected('private smtp detail'),
        ):
            response = self.invite()

        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert not TaskInvitation.objects.exists()
        assert mail.outbox == []


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='kando.gerenciador@gmail.com',
    FRONTEND_BASE_URL='http://insecure.example',
)
class TaskInvitationFrontendURLTests(APITestCase):
    def test_non_https_frontend_url_prevents_sending_and_rolls_back_invitation(self):
        inviter = User.objects.create_user('inviter@example.com', 'InviterPassword!123')
        invitee = User.objects.create_user('invitee@example.com', 'InviteePassword!123')
        board = Board.objects.create(owner=inviter, title='Product')
        task = Task.objects.create(board=board, title='Prepare launch', created_by=inviter)
        self.client.force_authenticate(inviter)

        response = self.client.post(
            '/api/invitations/',
            {'task': task.pk, 'email': invitee.email},
            format='json',
        )

        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert not TaskInvitation.objects.exists()
