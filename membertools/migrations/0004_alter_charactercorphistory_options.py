# Generated by Django 4.2.13 on 2024-07-28 00:37

# Django
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("membertools", "0003_implement_titlefilter_add_title_requirement_flag"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="charactercorphistory",
            options={"ordering": ("-record_id",)},
        ),
    ]
