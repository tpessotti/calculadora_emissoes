"""Django form for UnidadeProdutiva."""
import json

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Layout, Row, Submit

from .models import UnidadeProdutiva


class UnidadeForm(forms.ModelForm):
    # Override JSONField as textarea for human-friendly editing
    inputs_raw = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 6}),
        required=False,
        label="Insumos (JSON)",
        help_text='Ex: [{"nome": "Energia Elétrica", "quantidade": 100, "escopo": "Escopo 2", "unidade": "MWh"}]',
    )
    outputs_raw = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}),
        required=False,
        label="Saídas (JSON)",
        help_text='Ex: [{"nome": "Produto A", "quantidade": 50, "unidade": "t"}]',
    )

    class Meta:
        model = UnidadeProdutiva
        fields = [
            "id_elo", "nome", "localizacao", "tecnologia",
            "periodos", "massa_input", "massa_output",
        ]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields["tecnologia"].queryset = \
                self.fields["tecnologia"].queryset.filter(owner=user)

        # Pre-populate raw JSON fields from existing instance
        if self.instance.pk:
            self.fields["inputs_raw"].initial = json.dumps(
                self.instance.inputs or [], ensure_ascii=False, indent=2
            )
            self.fields["outputs_raw"].initial = json.dumps(
                self.instance.outputs or [], ensure_ascii=False, indent=2
            )

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column("id_elo", css_class="col-md-4"),
                Column("nome", css_class="col-md-8"),
            ),
            Row(
                Column("localizacao", css_class="col-md-6"),
                Column("tecnologia", css_class="col-md-6"),
            ),
            Row(
                Column("massa_input", css_class="col-md-4"),
                Column("massa_output", css_class="col-md-4"),
                Column("periodos", css_class="col-md-4"),
            ),
            "inputs_raw",
            "outputs_raw",
            Submit("submit", "Salvar", css_class="btn btn-primary"),
        )

    def clean_inputs_raw(self):
        raw = self.cleaned_data.get("inputs_raw", "").strip()
        if not raw:
            return []
        try:
            value = json.loads(raw)
            if not isinstance(value, list):
                raise forms.ValidationError("Insumos deve ser uma lista JSON.")
            return value
        except json.JSONDecodeError as exc:
            raise forms.ValidationError(f"JSON inválido: {exc}") from exc

    def clean_outputs_raw(self):
        raw = self.cleaned_data.get("outputs_raw", "").strip()
        if not raw:
            return []
        try:
            value = json.loads(raw)
            if not isinstance(value, list):
                raise forms.ValidationError("Saídas deve ser uma lista JSON.")
            return value
        except json.JSONDecodeError as exc:
            raise forms.ValidationError(f"JSON inválido: {exc}") from exc

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.inputs = self.cleaned_data.get("inputs_raw") or []
        instance.outputs = self.cleaned_data.get("outputs_raw") or []
        if commit:
            instance.save()
        return instance
