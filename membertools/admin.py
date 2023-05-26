# Django
from django.contrib import admin
from django.contrib.admin.widgets import AdminTextInputWidget
from django.forms import ModelForm

from .models import (
    Application,
    ApplicationAction,
    ApplicationChoice,
    ApplicationForm,
    ApplicationQuestion,
    ApplicationResponse,
    ApplicationTitle,
    Character,
    CharacterUpdateStatus,
    Comment,
    Member,
    TitleFilter,
)


@admin.register(Member)
class MemberDetailAdmin(admin.ModelAdmin):
    list_display = [
        "main_character",
        "first_main_character",
        "get_user",
        "awarded_title",
        "first_joined",
        "last_joined",
    ]
    readonly_fields = [
        "first_joined",
        "last_joined",
    ]
    search_fields = [
        "main_character__character_name",
        "first_main_character__character_name",
        "main_character__character_ownership__user__username",
    ]
    list_filter = [
        "awarded_title",
        "first_joined",
        "last_joined",
    ]

    @admin.display(
        description="User",
        ordering="main_character__character_ownership__user",
    )
    def get_user(self, obj):
        return obj.user


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = (
        "eve_character",
        "corporation",
        "alliance",
        "get_main",
        "applied_title",
        "get_last_login",
        "location",
    )
    list_filter = (
        "applied_title",
        "eve_character__memberaudit_character__online_status__last_login",
    )
    readonly_fields = (
        "birthday",
        "description",
        "security_status",
        "title",
    )
    search_fields = [
        "eve_character__character_name",
        "eve_character__character_ownership__user__profile__main_character__character_name",
    ]

    @admin.display(
        description="Main",
        ordering="eve_character__character_ownership__user__profile__main_character",
    )
    def get_main(self, obj):
        return obj.main_character

    @admin.display(
        description="Last Login",
        ordering="eve_character__memberaudit_character__online_status__last_login",
    )
    def get_last_login(self, obj):
        return obj.online_last_login


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    exclude = (
        "approved",
        "review_needed",
        "reviewer_character",
    )
    list_display = (
        "eve_character",
        "main_character",
        "user",
        "submitted_on",
        "closed_on",
        "status",
        "status_on",
        "decision",
        "reviewer",
    )
    list_filter = (
        "status",
        "decision",
        "submitted_on",
        "closed_on",
        "status_on",
        ("reviewer", admin.RelatedOnlyFieldListFilter),
    )
    readonly_fields = (
        "submitted_on",
        "status_on",
        "decision_on",
        "closed_on",
    )
    ordering = ["-submitted_on"]
    search_fields = [
        "eve_character__character_name",
        "eve_character__character_ownership__user__profile__main_character__character_name",
        "reviewer__character_name",
    ]


class ApplicationFormForm(ModelForm):
    class Meta:
        model = ApplicationForm
        widgets = {
            "accept_template_subject": AdminTextInputWidget(
                attrs={"style": "width: 45em;"}
            ),
            "reject_template_subject": AdminTextInputWidget(
                attrs={"style": "width: 45em;"}
            ),
        }
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["title"].widget.can_delete_related = False
        self.fields["title"].widget.can_change_related = False


@admin.register(ApplicationForm)
class ApplicationFormAdmin(admin.ModelAdmin):
    filter_horizontal = [
        "auditor_groups",
        "recruiter_groups",
        "manager_groups",
    ]
    list_display = ["corp", "title", "description"]
    form = ApplicationFormForm


class ChoiceInline(admin.TabularInline):
    model = ApplicationChoice
    extra = 0
    verbose_name_plural = "Choices (optional)"
    verbose_name = "Choice"


@admin.register(ApplicationQuestion)
class ApplicationQuestionAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {"fields": ["title", "help_text", "multi_select"]}),
    ]
    inlines = [ChoiceInline]


@admin.register(Comment)
class ApplicationCommentAdmin(admin.ModelAdmin):
    pass


@admin.register(ApplicationResponse)
class ApplicationResponseAdmin(admin.ModelAdmin):
    pass


@admin.register(ApplicationTitle)
class ApplicationTitleAdmin(admin.ModelAdmin):
    list_display = ["name", "priority"]
    ordering = ["priority"]


@admin.register(ApplicationAction)
class ApplicationActionAdmin(admin.ModelAdmin):
    list_display = [
        "get_character",
        "application",
        "get_appform",
        "action",
        "action_on",
        "action_by",
        "override_by",
    ]
    ordering = ["-action_on"]
    readonly_fields = [
        "get_character",
        "application",
        "get_appform",
        "action",
        "action_on",
        "action_by",
        "override_by",
    ]
    list_filter = [
        "application__form",
        "action",
        "action_on",
        ("action_by", admin.RelatedOnlyFieldListFilter),
        ("override_by", admin.RelatedOnlyFieldListFilter),
    ]
    search_fields = ["application__character", "action_by", "override_by"]

    @admin.display(
        description="Character",
        ordering="application__character",
    )
    def get_character(self, obj):
        return obj.application.character

    @admin.display(
        description="form",
        ordering="application__form",
    )
    def get_appform(self, obj):
        if obj.application.form.title:
            return f"{obj.application.form.corp}: {obj.application.form.title}"
        return f"{obj.application.form.corp}"


@admin.register(CharacterUpdateStatus)
class CharacterUpdateStatusAdmin(admin.ModelAdmin):
    fields = ["character", "status", "updated_on", "expires_on", "task_id"]
    list_display = ["character", "status", "updated_on", "expires_on", "task_id"]
    readonly_fields = ["character", "status", "updated_on"]


@admin.register(TitleFilter)
class TitleFilterAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
