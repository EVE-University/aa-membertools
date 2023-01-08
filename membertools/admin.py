from django.forms import ModelForm
from django.contrib import admin
from django.contrib.admin.widgets import AdminTextInputWidget

from .models import (
    Application,
    ApplicationChoice,
    Comment,
    ApplicationForm,
    ApplicationQuestion,
    ApplicationResponse,
    ApplicationTitle,
    ApplicationAction,
    Member,
    Character,
    CharacterUpdateStatus,
)


@admin.register(Member)
class MemberDetailAdmin(admin.ModelAdmin):
    list_display = ["get_main", "user", "awarded_title", "first_joined", "last_joined"]
    readonly_fields = ["first_joined", "last_joined"]
    search_fields = ["user__profile__main_character__character_name", "user"]

    def get_main(self, obj):
        return obj.main_character

    get_main.admin_order_field = "user__profile__main_character__character_name"
    get_main.short_description = "Main Char."


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = (
        "eve_character",
        "corporation",
        "alliance",
        "main_character",
        "online_last_login",
        "location",
    )
    readonly_fields = ("birthday", "description", "security_status", "title")
    search_fields = ["character", "main_character"]


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    exclude = (
        "approved",
        "review_needed",
        "reviewer_character",
    )
    list_display = (
        "character",
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
        "reviewer",
    )
    readonly_fields = ("submitted_on", "status_on", "closed_on")
    ordering = ["-submitted_on"]
    search_fields = [
        "character__character_name",
        "user__profile__main_character__character_name",
        "reviewer__profile__main_character__character_name",
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
        super(ApplicationFormForm, self).__init__(*args, **kwargs)
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
        "action_by",
        "override_by",
    ]
    search_fields = ["application__character", "action_by", "override_by"]

    def get_character(self, obj):
        return obj.application.character

    get_character.admin_order_field = "application__character"
    get_character.short_description = "Character"

    def get_appform(self, obj):
        if obj.application.form.title:
            return f"{obj.application.form.corp}: {obj.application.form.title}"
        return f"{obj.application.form.corp}"

    get_appform.admin_order_field = "application__form"
    get_appform.short_description = "form"


@admin.register(CharacterUpdateStatus)
class CharacterUpdateStatusAdmin(admin.ModelAdmin):
    fields = ["character", "status", "updated_on", "expires_on", "task_id"]
    list_display = ["character", "status", "updated_on", "expires_on", "task_id"]
    readonly_fields = ["character", "status", "updated_on"]
