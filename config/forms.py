from django import forms
from django.utils.translation import gettext_lazy as _


class UniqueNameMixin:
    """No two entries of one business share a name (ignoring case), so lists and pickers stay unambiguous."""

    def __init__(self, *args, business, **kwargs):
        super().__init__(*args, **kwargs)
        self.business = business

    def clean_name(self):
        name = self.cleaned_data["name"]
        model = self._meta.model
        if (
            model.objects.filter(business=self.business, name__iexact=name)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise forms.ValidationError(
                _("“%(name)s” already exists. Please choose another name."), params={"name": name}
            )
        return name


class BootstrapFormMixin:
    """Adds Bootstrap 5 classes to every widget, so templates can render fields with `as_field_group`."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")  # "Name" instead of Django's "Name:"
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxSelectMultiple):
                continue  # rendered by hand in the ingredient form
            if isinstance(widget, forms.CheckboxInput):
                css = "form-check-input"
            elif isinstance(widget, forms.Select):
                css = "form-select"
            else:
                css = "form-control"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css}".strip()
