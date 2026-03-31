import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='provider',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='orders',
                to='core.provider',
            ),
        ),
        migrations.AddField(
            model_name='order',
            name='referring_provider_name',
            field=models.CharField(blank=True, max_length=200),
        ),
    ]
