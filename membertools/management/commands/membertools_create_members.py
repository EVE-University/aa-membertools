# Django
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

# EVE Uni Member Tools
from membertools.app_settings import MEMBERTOOLS_MAIN_CORP_ID
from membertools.models import Character, Comment, Member


class Command(BaseCommand):
    help = "Initializes the Member with Main Characters that are in the Main Corp"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--main_corp_id", type=int, required=False)

    def handle(self, *args, **options):
        main_corp = options["main_corp_id"]
        if main_corp is None:
            main_corp = MEMBERTOOLS_MAIN_CORP_ID

        query = User.objects.select_related("profile__main_character").filter(
            profile__main_character__corporation_id=main_corp
        )

        for user in query:
            try:
                member = Member.objects.get(
                    main_character__character_ownership__user=user
                )
            except Member.DoesNotExist:
                member = Member.objects.create(
                    main_character=user.profile.main_character,
                    first_main_character=user.profile.main_character,
                )

            char_query = Character.objects.filter(
                eve_character__character_ownership__user=user
            )
            for char in char_query:
                char.member = member
                char.save()

                Comment.objects.filter(character=char).update(member=member)
