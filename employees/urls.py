# yourapp/urls.py
from django.urls import path
from .views import EmployeeView, AddFieldView,EmployeeDetailView

urlpatterns = [
    path('employees/', EmployeeView.as_view(), name='employee'),
    path('employees/add-field/', AddFieldView.as_view(), name='add-field'),
    path('employees/search/', EmployeeView.as_view(), name='employee-search'), 
    path('employees/<int:pk>/', EmployeeDetailView.as_view(), name='employee-detail'),
    path('employees/edit-field/', AddFieldView.as_view(), name='edit-field'),
]
