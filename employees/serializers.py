# # serializers.py
# from rest_framework import serializers
# from .models import Employee, EmployeeCustomField

# class EmployeeCustomFieldSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = EmployeeCustomField
#         fields = ['field_name', 'field_value']

# class EmployeeSerializer(serializers.ModelSerializer):
#     custom_fields = EmployeeCustomFieldSerializer(many=True)

#     class Meta:
#         model = Employee
#         fields = ['name', 'email', 'phone_number', 'custom_fields']

#     def create(self, validated_data):
#         custom_fields_data = validated_data.pop('custom_fields', [])
#         employee = Employee.objects.create(**validated_data)
#         for field_data in custom_fields_data:
#             EmployeeCustomField.objects.create(employee=employee, **field_data)
#         return employee
