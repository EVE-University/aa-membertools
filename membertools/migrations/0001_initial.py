# Generated by Django 3.2.16 on 2023-01-22 07:09

# Third Party
import sortedm2m.fields

# Django
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models

# AA EVE Uni Core
import membertools.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("esi", "0011_add_token_indices"),
        ("eveonline", "0015_factions"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="General",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
            ],
            options={
                "permissions": (
                    ("basic_access", "Can access the applicant areas"),
                    ("admin_access", "Can access admin areas"),
                    ("character_admin_access", "Can access the character list"),
                    ("application_admin_access", "Can access the application list"),
                    ("queue_admin_access", "Can access the queues"),
                ),
                "managed": False,
                "default_permissions": (),
            },
        ),
        migrations.CreateModel(
            name="Application",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "status",
                    models.SmallIntegerField(
                        choices=[
                            (1, "New"),
                            (2, "Under Review"),
                            (3, "Wait"),
                            (4, "Processed"),
                            (5, "Closed"),
                        ],
                        default=1,
                    ),
                ),
                ("status_on", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "last_status",
                    models.SmallIntegerField(
                        choices=[
                            (1, "New"),
                            (2, "Under Review"),
                            (3, "Wait"),
                            (4, "Processed"),
                            (5, "Closed"),
                        ],
                        default=1,
                    ),
                ),
                (
                    "decision",
                    models.SmallIntegerField(
                        choices=[
                            (0, "Pending"),
                            (1, "Accept"),
                            (2, "Reject"),
                            (3, "Withdraw"),
                        ],
                        default=0,
                    ),
                ),
                ("decision_on", models.DateTimeField(blank=True, null=True)),
                (
                    "submitted_on",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                ("closed_on", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "permissions": (
                    ("review_application", "Can review applications"),
                    ("reject_application", "Can reject applications"),
                    ("manage_application", "Can override actions on applications"),
                ),
            },
        ),
        migrations.CreateModel(
            name="ApplicationQuestion",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=254, verbose_name="Question")),
                ("help_text", models.CharField(blank=True, max_length=254, null=True)),
                ("multi_select", models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name="ApplicationTitle",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=64)),
                ("priority", models.SmallIntegerField(default=0)),
            ],
            options={
                "verbose_name": "Title",
                "verbose_name_plural": "Titles",
                "ordering": ["priority"],
            },
        ),
        migrations.CreateModel(
            name="Character",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("birthday", models.DateTimeField(null=True)),
                ("description", models.TextField(null=True)),
                ("security_status", models.FloatField(default=None, null=True)),
                ("title", models.TextField(null=True)),
                ("deleted", models.BooleanField(default=False)),
                (
                    "alliance",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="eveonline.eveallianceinfo",
                    ),
                ),
                (
                    "applied_title",
                    models.ForeignKey(
                        blank=True,
                        default=membertools.models._get_app_title_none_id,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="membertools.applicationtitle",
                    ),
                ),
                (
                    "corporation",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="eveonline.evecorporationinfo",
                    ),
                ),
                (
                    "eve_character",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="next_character",
                        to="eveonline.evecharacter",
                    ),
                ),
                (
                    "faction",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="eveonline.evefactioninfo",
                    ),
                ),
            ],
            options={
                "verbose_name": "Character",
                "verbose_name_plural": "Characters",
                "ordering": ["eve_character__character_name"],
            },
        ),
        migrations.CreateModel(
            name="Member",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("first_joined", models.DateTimeField(blank=True, null=True)),
                ("last_joined", models.DateTimeField(blank=True, null=True)),
                (
                    "awarded_title",
                    models.ForeignKey(
                        blank=True,
                        default=membertools.models._get_app_title_none_id,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="membertools.applicationtitle",
                    ),
                ),
                (
                    "first_main_character",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="eveonline.evecharacter",
                    ),
                ),
                (
                    "main_character",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="next_member",
                        to="eveonline.evecharacter",
                    ),
                ),
            ],
            options={
                "verbose_name": "Member",
                "verbose_name_plural": "Members",
                "ordering": ["id"],
            },
        ),
        migrations.CreateModel(
            name="Comment",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("text", models.TextField()),
                ("created", models.DateTimeField(auto_now_add=True)),
                (
                    "application",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="comments",
                        to="membertools.application",
                    ),
                ),
                (
                    "character",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="comments",
                        to="membertools.character",
                    ),
                ),
                (
                    "member",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="comments",
                        to="membertools.member",
                    ),
                ),
                (
                    "poster",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="eveonline.evecharacter",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="CharacterUpdateStatus",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "status",
                    models.PositiveSmallIntegerField(
                        choices=[(1, "Okay"), (2, "Error"), (3, "Updating")]
                    ),
                ),
                (
                    "updated_on",
                    models.DateTimeField(default=django.utils.timezone.now, null=True),
                ),
                ("last_modified_on", models.DateTimeField(null=True)),
                ("expires_on", models.DateTimeField(null=True)),
                ("task_id", models.UUIDField(null=True)),
                (
                    "character",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="update_status",
                        to="membertools.character",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="CharacterLink",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "source",
                    models.SmallIntegerField(
                        choices=[
                            (1, "ESI Verified"),
                            (2, "Previous ESI"),
                            (3, "Manually Added"),
                        ]
                    ),
                ),
                ("linked_on", models.DateTimeField()),
                ("reason", models.TextField(max_length=1024)),
                (
                    "character",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="membertools.character",
                    ),
                ),
                (
                    "esi_token",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="esi.token",
                    ),
                ),
                (
                    "linked_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="eveonline.evecharacter",
                    ),
                ),
                (
                    "member",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="character_links",
                        to="membertools.member",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="CharacterCorpHistory",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("record_id", models.PositiveIntegerField()),
                ("is_deleted", models.BooleanField(default=False)),
                ("is_last", models.BooleanField(default=False)),
                ("start_date", models.DateTimeField()),
                ("end_date", models.DateTimeField(null=True)),
                (
                    "character",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="corporation_history",
                        to="membertools.character",
                    ),
                ),
                (
                    "corporation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="eveonline.evecorporationinfo",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="character",
            name="member",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="character",
                to="membertools.member",
            ),
        ),
        migrations.CreateModel(
            name="ApplicationResponse",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("answer", models.TextField()),
                (
                    "application",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="responses",
                        to="membertools.application",
                    ),
                ),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="membertools.applicationquestion",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ApplicationForm",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "description",
                    models.TextField(blank=True, max_length=2048, null=True),
                ),
                ("pre_text", models.TextField(blank=True, default="", max_length=4096)),
                (
                    "post_text",
                    models.TextField(blank=True, default="", max_length=4096),
                ),
                (
                    "accept_template_subject",
                    models.TextField(default="", max_length=1000),
                ),
                (
                    "accept_template_body",
                    models.TextField(default="", max_length=10000),
                ),
                (
                    "reject_template_subject",
                    models.TextField(default="", max_length=1000),
                ),
                (
                    "reject_template_body",
                    models.TextField(default="", max_length=10000),
                ),
                (
                    "allow_applied",
                    models.ManyToManyField(
                        related_name="applied",
                        to="membertools.ApplicationTitle",
                        verbose_name="Allowed Applied Titles",
                    ),
                ),
                (
                    "allow_awarded",
                    models.ManyToManyField(
                        related_name="awarded",
                        to="membertools.ApplicationTitle",
                        verbose_name="Allowed Awarded Titles",
                    ),
                ),
                (
                    "auditor_groups",
                    models.ManyToManyField(
                        blank=True,
                        related_name="next_form_auditor_groups",
                        to="auth.Group",
                    ),
                ),
                (
                    "corp",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="next_forms",
                        to="eveonline.evecorporationinfo",
                    ),
                ),
                (
                    "manager_groups",
                    models.ManyToManyField(
                        blank=True,
                        related_name="next_form_manager_groups",
                        to="auth.Group",
                    ),
                ),
                (
                    "questions",
                    sortedm2m.fields.SortedManyToManyField(
                        blank=True, help_text=None, to="membertools.ApplicationQuestion"
                    ),
                ),
                (
                    "recruiter_groups",
                    models.ManyToManyField(
                        blank=True,
                        related_name="next_form_recruiter_groups",
                        to="auth.Group",
                    ),
                ),
                (
                    "title",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="membertools.applicationtitle",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ApplicationChoice",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "choice_text",
                    models.CharField(max_length=200, verbose_name="Choice"),
                ),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="choices",
                        to="membertools.applicationquestion",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ApplicationAction",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "action",
                    models.SmallIntegerField(
                        choices=[
                            (1, "Start Review"),
                            (2, "Accept"),
                            (3, "Reject"),
                            (4, "Wait"),
                            (5, "Release"),
                            (6, "Close"),
                            (7, "Withdraw"),
                        ]
                    ),
                ),
                ("action_on", models.DateTimeField(auto_now_add=True)),
                (
                    "action_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="eveonline.evecharacter",
                    ),
                ),
                (
                    "application",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="actions",
                        to="membertools.application",
                    ),
                ),
                (
                    "override_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="eveonline.evecharacter",
                    ),
                ),
            ],
            options={
                "ordering": ["-action_on"],
            },
        ),
        migrations.AddField(
            model_name="application",
            name="character",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="applications",
                to="membertools.character",
            ),
        ),
        migrations.AddField(
            model_name="application",
            name="decision_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="eveonline.evecharacter",
            ),
        ),
        migrations.AddField(
            model_name="application",
            name="eve_character",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="next_applications",
                to="eveonline.evecharacter",
            ),
        ),
        migrations.AddField(
            model_name="application",
            name="form",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="applications",
                to="membertools.applicationform",
            ),
        ),
        migrations.AddField(
            model_name="application",
            name="reviewer",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="eveonline.evecharacter",
            ),
        ),
        migrations.AddIndex(
            model_name="characterupdatestatus",
            index=models.Index(
                fields=["expires_on"], name="membertools_expires_c79470_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="charactercorphistory",
            index=models.Index(
                fields=["character"], name="membertools_charact_62a412_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="charactercorphistory",
            index=models.Index(
                fields=["record_id"], name="membertools_record__6bc083_idx"
            ),
        ),
        migrations.AddConstraint(
            model_name="charactercorphistory",
            constraint=models.UniqueConstraint(
                fields=("character", "record_id"), name="unique_character_record"
            ),
        ),
        migrations.AlterUniqueTogether(
            name="applicationresponse",
            unique_together={("question", "application")},
        ),
        migrations.AddConstraint(
            model_name="applicationform",
            constraint=models.UniqueConstraint(
                fields=("corp", "title"), name="corp title unique apps"
            ),
        ),
    ]
