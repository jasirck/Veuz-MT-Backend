from django.db import connection
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.files.storage import default_storage
from django.db import DatabaseError
from .models import Employee
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def delete_file_if_exists(file_path):
    if file_path and Path(file_path).exists():
        Path(file_path).unlink()

# Helper function to fetch column type
def get_column_type(column_name):
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA table_info(employees_employee)")  # Update table name if different
        columns_info = cursor.fetchall()
        for column in columns_info:
            if column[1] == column_name:
                return column[2]
    return 'unknown'


# Helper function for deleting old files
def delete_file_if_exists(file_path):
    if file_path and default_storage.exists(file_path):
        default_storage.delete(file_path)


class EmployeeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Retrieve all employees or filter by a search query."""
        search_query = request.GET.get('search', None)
        with connection.cursor() as cursor:
            if search_query:
                query = """
                    SELECT * FROM employees_employee 
                    WHERE LOWER(name) LIKE LOWER(%s)
                """
                cursor.execute(query, [f"%{search_query}%"])
            else:
                cursor.execute("SELECT * FROM employees_employee")

            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()

        data = [dict(zip(columns, row)) for row in rows]
        response_data = {
            'columns': columns,
            'column_types': [get_column_type(col) for col in columns],
            'data': data,
        }
        return Response(response_data, status=status.HTTP_200_OK)

    def post(self, request):
        """Create a new employee entry with support for file uploads."""
        employee_data = {}
        file_fields = {}

        for key, value in request.data.items():
            if isinstance(value, InMemoryUploadedFile):
                file_fields[key] = value
            else:
                employee_data[key] = value

        employee_data = {key: value for key, value in employee_data.items() if value}
        if not employee_data:
            return Response({"error": "No valid data provided"}, status=status.HTTP_400_BAD_REQUEST)

        columns = ', '.join(employee_data.keys())
        values_placeholder = ', '.join(['%s'] * len(employee_data))
        query = f"INSERT INTO employees_employee ({columns}) VALUES ({values_placeholder})"

        try:
            with connection.cursor() as cursor:
                cursor.execute(query, list(employee_data.values()))
                employee_id = cursor.lastrowid

                if not employee_id:
                    return Response({"error": "Failed to retrieve employee ID"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                for file_field, file in file_fields.items():
                    file_path = default_storage.save(f'{file_field}s/{file.name}', file)
                    cursor.execute(
                        f"UPDATE employees_employee SET {file_field} = %s WHERE id = %s",
                        [file_path, employee_id]
                    )
    
            return Response({"message": "Employee created successfully"}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AddFieldView(APIView):
    permission_classes = [IsAuthenticated]
    sql_type_mapping = {
        'char': 'VARCHAR(150)',
        'text': 'VARCHAR(300)',
        'number': 'INTEGER',
        'date': 'DATE',
        'email': 'VARCHAR(254)',
        'phone': 'VARCHAR(20)',
        'url': 'VARCHAR(720)',
        'checkbox': 'BOOLEAN',
        'image': 'BLOB',
        'file.txt': 'BLOB',
    }

    def post(self, request):
        """Add a new column to the Employee table."""
        field_name = request.data.get('field_name')
        field_type = request.data.get('field_type')

        if not field_name or not field_type or field_type not in self.sql_type_mapping:
            return Response({"error": "Invalid field name or type"}, status=status.HTTP_400_BAD_REQUEST)

        sql = f"ALTER TABLE employees_employee ADD COLUMN {field_name} {self.sql_type_mapping[field_type]}"
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql)
            return Response({"message": f"Field '{field_name}' added successfully"}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        """Rename an existing column in the Employee table."""
        old_field_name = request.data.get('old_field_name')
        new_field_name = request.data.get('new_field_name')

        if not old_field_name or not new_field_name:
            return Response({"error": "Both old and new field names are required"}, status=status.HTTP_400_BAD_REQUEST)

        sql = f"ALTER TABLE employees_employee RENAME COLUMN {old_field_name} TO {new_field_name}"
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql)
            return Response({"message": f"Field '{old_field_name}' renamed successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        """Delete a column from the Employee table."""
        field_name = request.data.get('field_name')

        if not field_name:
            return Response({"error": "Field name is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cursor = connection.cursor()
            cursor.execute("PRAGMA table_info(employees_employee)")
            columns = [column[1] for column in cursor.fetchall()]

            if field_name not in columns:
                return Response({"error": f"Field '{field_name}' not found"}, status=status.HTTP_404_NOT_FOUND)

            new_columns = [col for col in columns if col != field_name]
            cursor.execute(f"CREATE TABLE employees_employee_temp ({', '.join(new_columns)})")
            cursor.execute(f"INSERT INTO employees_employee_temp ({', '.join(new_columns)}) SELECT {', '.join(new_columns)} FROM employees_employee")
            cursor.execute("DROP TABLE employees_employee")
            cursor.execute("ALTER TABLE employees_employee_temp RENAME TO employees_employee")

            return Response({"message": f"Field '{field_name}' deleted successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EmployeeDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        """Retrieve a single employee by ID."""
        query = "SELECT * FROM employees_employee WHERE id = %s"
        employee = Employee.objects.raw(query, [pk])
        
        if not employee:
            return Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)

        columns = [col[0] for col in connection.cursor().description]
        data = {columns[i]: getattr(employee[0], columns[i]) for i in range(len(columns))}
        return Response(data, status=status.HTTP_200_OK)
    

    


    def put(self, request, pk):
        """Update employee details with support for file fields using raw SQL only."""
        non_file_data = {key: value for key, value in request.POST.items()}
        file_fields = {key: file for key, file in request.FILES.items()}

        # Build SQL for updating non-file data
        if non_file_data:
            columns = ', '.join([f"{key} = %s" for key in non_file_data.keys()])
            values = list(non_file_data.values()) + [pk]
            query = f"UPDATE employees_employee SET {columns} WHERE id = %s"

            try:
                with connection.cursor() as cursor:
                    cursor.execute(query, values)
                    if cursor.rowcount == 0:
                        return Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)
            except DatabaseError as db_error:
                logger.error("Database error updating employee '%s': %s", pk, str(db_error))
                return Response({"error": "Database error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Handle file fields
        if file_fields:
            for field, file in file_fields.items():
                # Define file path, assuming a media directory and employee ID folder
                file_path = f"media/{field}s/{file.name}"
                with open(file_path, 'wb+') as destination:
                    for chunk in file.chunks():
                        destination.write(chunk)

                # Update the file path in the database using raw SQL
                query = f"UPDATE employees_employee SET {field} = %s WHERE id = %s"
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(query, [f"{field}s/{file.name}", pk])
                except DatabaseError as db_error:
                    logger.error("Database error updating file for employee '%s': %s", pk, str(db_error))
                    return Response({"error": "Database error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"message": "Employee updated successfully"}, status=status.HTTP_200_OK)


    def delete(self, request, pk):
        """Delete an employee by ID."""
        query = "DELETE FROM employees_employee WHERE id = %s"
        
        with connection.cursor() as cursor:
            cursor.execute(query, [pk])
            if cursor.rowcount == 0:
                return Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)
        
        return Response({"message": "Employee deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
