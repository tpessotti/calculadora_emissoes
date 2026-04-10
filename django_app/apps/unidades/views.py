"""
Unidades Produtivas — HTML views.
"""
import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView,
)

from framework.calc.engine import EmissionEngine
from framework.calc.fatores import FatorIndex

from apps.conexoes.models import Conexao
from apps.fatores.models import FatorEmissao

from .forms import UnidadeForm
from .models import UnidadeProdutiva

logger = logging.getLogger(__name__)


class UnidadeListView(LoginRequiredMixin, ListView):
    model = UnidadeProdutiva
    template_name = "unidades/list.html"
    context_object_name = "unidades"
    paginate_by = 25

    def get_queryset(self):
        qs = UnidadeProdutiva.objects.filter(owner=self.request.user).select_related("tecnologia")

        # Filters
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(nome__icontains=q) | qs.filter(id_elo__icontains=q)

        loc = self.request.GET.get("localizacao", "").strip()
        if loc:
            qs = qs.filter(localizacao__icontains=loc)

        tec = self.request.GET.get("tecnologia", "").strip()
        if tec:
            qs = qs.filter(tecnologia__nome__icontains=tec)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter_q"] = self.request.GET.get("q", "")
        ctx["filter_loc"] = self.request.GET.get("localizacao", "")
        ctx["filter_tec"] = self.request.GET.get("tecnologia", "")
        return ctx


class UnidadeDetailView(LoginRequiredMixin, DetailView):
    model = UnidadeProdutiva
    template_name = "unidades/detail.html"
    context_object_name = "unidade"

    def get_queryset(self):
        return UnidadeProdutiva.objects.filter(owner=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        unidade = self.get_object()

        # Build connections for this unit
        ctx["conexoes_saida"] = Conexao.objects.filter(
            origem=unidade, owner=self.request.user
        ).select_related("destino")
        ctx["conexoes_entrada"] = Conexao.objects.filter(
            destino=unidade, owner=self.request.user
        ).select_related("origem")

        # Calculate emissions
        ano = self.request.user.active_year
        fatores = list(FatorEmissao.objects.values(
            "consumivel", "escopo", "ano", "kgCO2e_unid", "fator_emissao",
            "grupo_consumivel", "unidade"
        ))
        if fatores:
            try:
                idx = FatorIndex(fatores)
                engine = EmissionEngine(idx)
                result = engine.calculate_unit(
                    unidade_id=unidade.id_elo,
                    unidade_nome=unidade.nome,
                    inputs=unidade.inputs,
                    massa_output=unidade.massa_output,
                    ano_ref=ano,
                )
                ctx["emission_result"] = result
            except Exception:
                logger.exception("Erro ao calcular emissões para unidade %s", unidade.pk)

        return ctx


class UnidadeCreateView(LoginRequiredMixin, CreateView):
    model = UnidadeProdutiva
    form_class = UnidadeForm
    template_name = "unidades/form.html"
    success_url = reverse_lazy("unidades:list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, f"Unidade '{form.instance.nome}' criada com sucesso.")
        return super().form_valid(form)


class UnidadeUpdateView(LoginRequiredMixin, UpdateView):
    model = UnidadeProdutiva
    form_class = UnidadeForm
    template_name = "unidades/form.html"

    def get_queryset(self):
        return UnidadeProdutiva.objects.filter(owner=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse_lazy("unidades:detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, f"Unidade '{form.instance.nome}' atualizada.")
        return super().form_valid(form)


class UnidadeDeleteView(LoginRequiredMixin, DeleteView):
    model = UnidadeProdutiva
    template_name = "unidades/confirm_delete.html"
    success_url = reverse_lazy("unidades:list")

    def get_queryset(self):
        return UnidadeProdutiva.objects.filter(owner=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, f"Unidade '{self.object.nome}' removida.")
        return super().form_valid(form)
