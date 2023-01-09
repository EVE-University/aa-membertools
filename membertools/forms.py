from django import forms

from django.utils.translation import gettext_lazy as _

from .models import Application, Comment

from allianceauth.services.hooks import get_extension_logger

logger = get_extension_logger(__name__)


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["application", "text"]

    def __init__(self, detail, *args, **kwargs):
        super(CommentForm, self).__init__(*args, **kwargs)
        self.fields["application"].queryset = Application.objects.filter(
            character=detail
        )
        if self.instance and self.instance.text:
            # Auto focus text box when editing.
            self.fields["text"].widget.attrs.update({"autofocus": "autofocus"})


class HRCharDetailCommentForm(forms.Form):
    comment = forms.CharField(widget=forms.Textarea, required=False, label=_("Comment"))


class SearchForm(forms.Form):
    search = forms.CharField(max_length=254, required=False, label=_("Search"))

    def __init__(self, *args, **kwargs):
        placeholder = kwargs.pop("placeholder")

        super(SearchForm, self).__init__(*args, **kwargs)

        if placeholder:
            self.fields["search"].widget.attrs["placeholder"] = placeholder
