from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView
from .models import Tecnologia

class TecnologiaListView(LoginRequiredMixin, ListView):
    model = Tecnologia
    template_name = 'tecnologias/list.html'
    context_object_name = 'tecnologias'
    def get_queryset(self):
        return Tecnologia.objects.filter(owner=self.request.user)

class TecnologiaCreateView(LoginRequiredMixin, CreateView):
    model = Tecnologia
    fields = ['nome', 'descricao', 'insumos']
    template_name = 'tecnologias/form.html'
    success_url = reverse_lazy('tecnologias:list')
    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

class TecnologiaDeleteView(LoginRequiredMixin, DeleteView):
    model = Tecnologia
    template_name = 'tecnologias/confirm_delete.html'
    success_url = reverse_lazy('tecnologias:list')
    def get_queryset(self):
        return Tecnologia.objects.filter(owner=self.request.user)
