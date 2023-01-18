# Generated by Django 4.0.8 on 2023-01-18 05:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('eveonline', '0017_alliance_and_corp_names_are_not_unique'),
        ('membertools', '0008_character_faction'),
    ]

    operations = [
        migrations.AlterField(
            model_name='character',
            name='alliance',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='eveonline.eveallianceinfo'),
        ),
        migrations.AlterField(
            model_name='character',
            name='faction',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='eveonline.evefactioninfo'),
        ),
    ]
