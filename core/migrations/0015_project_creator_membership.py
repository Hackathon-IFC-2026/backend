from django.db import migrations


def registrar_criadores(apps, schema_editor):
    Projeto = apps.get_model('core', 'Projeto')
    Participante = apps.get_model('core', 'ParticipanteProjeto')
    db = schema_editor.connection.alias
    for projeto in Projeto.objects.using(db).all().iterator():
        Participante.objects.using(db).update_or_create(
            projeto_id=projeto.pk, usuario_id=projeto.criado_por_id, defaults={'papel': 'admin'}
        )


class Migration(migrations.Migration):
    dependencies = [('core', '0014_projeto_materialapoio_tarefa_comentario_checklist_and_more')]
    operations = [migrations.RunPython(registrar_criadores, migrations.RunPython.noop)]
