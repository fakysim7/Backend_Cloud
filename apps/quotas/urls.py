from django.urls import path
from .views import QuotaDetailView

urlpatterns = [
    path('quota/', QuotaDetailView.as_view(), name='quota-detail'),
]
