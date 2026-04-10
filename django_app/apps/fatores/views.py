from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from .models import FatorEmissao

class FatorEmissaoListView(LoginRequiredMixin, ListView):
    model = FatorEmissao
    template_name = 'fatores/list.html'
    context_object_name = 'fatores'
    paginate_by = 50

    def get_queryset(self):
        qs = FatorEmissao.objects.all()
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(consumivel__icontains=q) | qs.filter(grupo_consumivel__icontains=q)
        escopo = self.request.GET.get('escopo', '').strip()
        if escopo:
            qs = qs.filter(escopo=escopo)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['filter_q'] = self.request.GET.get('q', '')
        ctx['filter_escopo'] = self.request.GET.get('escopo', '')
        ctx['escopos'] = ['Escopo 1', 'Escopo 2', 'Escopo 3']
        return ctx
