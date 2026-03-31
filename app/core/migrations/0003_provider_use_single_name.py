from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_order_add_referring_provider_name'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='provider',
            name='first_name',
        ),
        migrations.RemoveField(
            model_name='provider',
            name='last_name',
        ),
        migrations.AddField(
            model_name='provider',
            name='name',
            field=models.CharField(default='', max_length=200),
            preserve_default=False,
        ),
    ]
