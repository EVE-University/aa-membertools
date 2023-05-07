# Django
from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction

# Alliance Auth
from allianceauth.eveonline.models import (
    EveCharacter,
    EveCorporationInfo,
    EveFactionInfo,
)

# EVE Uni Member Tools
from membertools.models import (
    Application,
    ApplicationChoice,
    ApplicationForm,
    ApplicationQuestion,
    ApplicationResponse,
    Character,
    Comment,
)


class Command(BaseCommand):
    help = "Imports data from HRAppsNext database. Shouldn't be ran after any non-imported data is present in membertools."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--confirm",
            action="store_true",
            required=True,
            help="Provide this flag to confirm you wish to import",
        )

    def _import_app_forms(self):
        HRNApplicationForm = apps.get_model("hrappsnext", "ApplicationForm")
        HRNApplicationQuestion = apps.get_model("hrappsnext", "ApplicationQuestion")
        HRNApplicationChoice = apps.get_model("hrappsnext", "ApplicationChoice")

        for question in HRNApplicationQuestion.objects.all():
            new_question, created = ApplicationQuestion.objects.update_or_create(
                id=question.id,
                defaults={
                    "title": question.title,
                    "help_text": question.help_text,
                    "multi_select": question.multi_select,
                },
            )

            if created:
                HRNApplicationChoice.objects.filter(
                    question_id=new_question.id
                ).delete()

            for choice in HRNApplicationChoice.objects.all():
                ApplicationChoice.objects.update_or_create(
                    id=choice.id,
                    defaults={
                        "question": new_question,
                        "choice_text": choice.choice_text,
                    },
                )

        for form in HRNApplicationForm.objects.all():
            new_form, created = ApplicationForm.objects.update_or_create(
                id=form.id,
                defaults={
                    "corp": form.corp,
                    "accept_template_subject": form.accept_template_subject,
                    "accept_template_body": form.accept_template_body,
                    "reject_template_subject": form.reject_template_subject,
                    "reject_template_body": form.reject_template_body,
                },
            )

            if created:
                new_form.questions.clear()
                new_form.recruiter_groups.clear()
                new_form.manager_groups.clear()

            for question in form.questions.all():
                new_question = ApplicationQuestion.objects.get(id=question.id)
                new_form.questions.add(new_question)

            for group in form.recruiter_groups.all():
                new_form.recruiter_groups.add(group)

            for group in form.manager_groups.all():
                new_form.manager_groups.add(group)

    def _import_apps(self):
        HRNApplication = apps.get_model("hrappsnext", "Application")
        HRNApplicationResponse = apps.get_model("hrappsnext", "ApplicationResponse")
        HRNApplicationComment = apps.get_model("hrappsnext", "ApplicationComment")

        for app in HRNApplication.objects.all():
            try:
                corp = app.character.corporation
            except EveCorporationInfo.DoesNotExist:
                corp = EveCorporationInfo.objects.create_corporation(
                    app.character.corporation_id
                )

            try:
                faction = app.character.faction
            except EveFactionInfo.DoesNotExist:
                faction = EveFactionInfo.objects.create(
                    faction_id=app.character.faction_id,
                    faction_name=app.character.faction_name,
                )

            char, created = Character.objects.update_or_create(
                eve_character__character_id=app.character.character_id,
                defaults={
                    "eve_character": app.character,
                    "corporation": corp,
                    "alliance": corp.alliance,
                    "faction": faction,
                },
            )
            if app.approved is not None:
                status = Application.STATUS_CLOSED
                decision = (
                    Application.DECISION_ACCEPT
                    if app.approved
                    else Application.DECISION_REJECT
                )
            elif app.review_needed:
                status = Application.STATUS_WAIT
                decision = Application.DECISION_PENDING
            else:
                status = Application.STATUS_NEW
                decision = Application.DECISION_PENDING

            new_app, __ = Application.objects.update_or_create(
                id=app.id,
                defaults={
                    "form": ApplicationForm.objects.get(id=app.form.id),
                    "character": char,
                    "eve_character": app.character,
                    "status": status,
                    "status_on": app.created,
                    "decision": decision,
                    "decision_on": app.created,
                    "decision_by": app.reviewer_character
                    if decision != Application.DECISION_PENDING
                    else None,
                    "reviewer": app.reviewer_character,
                    "submitted_on": app.created,
                    "closed_on": app.created
                    if status == Application.STATUS_CLOSED
                    else None,
                },
            )

            for resp in HRNApplicationResponse.objects.filter(application=app.id):
                ApplicationResponse.objects.update_or_create(
                    id=resp.id,
                    defaults={
                        "question": ApplicationQuestion.objects.get(
                            id=resp.question.id
                        ),
                        "application": new_app,
                        "answer": resp.answer,
                    },
                )

            for comment in HRNApplicationComment.objects.filter(application=app.id):
                poster = comment.user.profile.main_character
                if not poster:
                    poster = EveCharacter.objects.get(
                        character_name=str(comment.user).replace("_", " ")
                    )
                Comment.objects.update_or_create(
                    id=comment.id,
                    defaults={
                        "application": new_app,
                        "character": char,
                        "poster": poster,
                        "created": comment.created,
                        "text": comment.text,
                    },
                )

    def handle(self, *args, **options):
        if not apps.is_installed("hrappsnext"):
            self.stderr.write("HRAppsnext is not installed.")
            exit()

        if not options["confirm"]:
            exit()

        with transaction.atomic():
            self._import_app_forms()
            self._import_apps()

        self.stdout.write("HRAppsnext import complete.")
