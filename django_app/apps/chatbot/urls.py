from django.urls import path
from . import views

app_name = "chatbot"

urlpatterns = [
    path("", views.ChatbotView.as_view(), name="chat"),
    path("api/message/", views.ChatMessageAPI.as_view(), name="message"),
]
