from django.db import connection
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
# from .models import Employee
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.files.storage import default_storage
import os


class EmployeeView(APIView):
    def get_column_type(self, column_name):
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA table_info(employees_employee)")  # Adjust to your actual table name
            columns_info = cursor.fetchall()

        # Find the column type for the specified column name
        for column in columns_info:
            if column[1] == column_name:  # column[1] is the column name
                return column[2]  # column[2] is the column type
        return 'unknown'

    def get(self, request):
        search_query = request.GET.get('search', None)
        with connection.cursor() as cursor:
            if search_query:
                query = """
                    SELECT * FROM employees_employee 
                    WHERE LOWER(name) LIKE LOWER(%s)
                """
                cursor.execute(query, [f"%{search_query}%"])
            else:
                cursor.execute("SELECT * FROM employees_employee")  # Get all employees

            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()

        # Prepare the data in a structured format
        data = [dict(zip(columns, row)) for row in rows]

        # Prepare the response with column types
        response_data = {
            'columns': columns,
            'column_types': [self.get_column_type(col) for col in columns],  # Fetch column types dynamically
            'data': data,
        }

        return Response(response_data, status=status.HTTP_200_OK)
    
    def post(self, request):
        """Create a new employee entry based on the provided fields."""
        employee_data = {}
        file_fields = {}

    # Separate regular fields and file fields
        for key, value in request.data.items():
            if isinstance(value, InMemoryUploadedFile):
                file_fields[key] = value
            else:
                employee_data[key] = value

        # Filter out empty fields from employee_data
        employee_data = {key: value for key, value in employee_data.items() if value}

        if not employee_data:
            return Response({"error": "No valid data provided"}, status=status.HTTP_400_BAD_REQUEST)

        columns = ', '.join(employee_data.keys())
        values_placeholder = ', '.join(['%s'] * len(employee_data))
        query = f"INSERT INTO employees_employee ({columns}) VALUES ({values_placeholder})"

        try:
            with connection.cursor() as cursor:
                # Insert non-file data
                cursor.execute(query, list(employee_data.values()))
                print("Record inserted successfully.")  # Debugging line

                # Retrieve the new employee's ID
                employee_id = cursor.lastrowid
                print("Retrieved employee_id:", employee_id)  # Debugging line

                if not employee_id:
                    return Response({"error": "Failed to retrieve employee ID"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                # Handle file uploads, saving files and updating file paths in employee record
                for file_field, file in file_fields.items():
                    file_path = default_storage.save(f'{file_field}s/{file.name}', file)
                    cursor.execute(
                        f"UPDATE employees_employee SET {file_field} = %s WHERE id = %s",
                        [file_path, employee_id]
                    )
                    print(f"File saved and path updated for field '{file_field}': {file_path}")  # Debugging line
    
            return Response({"message": "Employee created successfully"}, status=status.HTTP_201_CREATED)
        except Exception as e:
            print("Error during employee creation:", str(e))  # Debugging line
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



    
class AddFieldView(APIView):
    def post(self, request):
        """Add a new field to the Employee table."""
        field_name = request.data.get('field_name')
        field_type = request.data.get('field_type')

        if not field_name or not field_type:
            return Response({"error": "Field name and type are required"}, status=status.HTTP_400_BAD_REQUEST)

        # Prepare the SQL statement to alter the t  able
        sql_type_mapping = {
            'text': 'VARCHAR(255)',
            'number': 'INTEGER',
            'date': 'DATE',
            'email': 'VARCHAR(255)',
            'phone': 'VARCHAR(20)',
            'url': 'VARCHAR(720)',
            'checkbox': 'BOOLEAN',
            'image': 'BLOB',  # For storing image file paths
            'file.txt': 'BLOB',  # For storing file binary data (if needed)
        }

        # Check if the provided field type is valid
        if field_type not in sql_type_mapping:
            return Response({"error": "Invalid field type"}, status=status.HTTP_400_BAD_REQUEST)

        sql = f"ALTER TABLE employees_employee ADD COLUMN {field_name} {sql_type_mapping[field_type]}"
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql)
            return Response({"message": f"Field '{field_name}' added successfully"}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def put(self, request):
        """Edit an existing field in the Employee table."""
        old_field_name = request.data.get('old_field_name')
        new_field_name = request.data.get('new_field_name')

        if not old_field_name or not new_field_name:
            return Response({"error": "Both old and new field names are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            sql = f"ALTER TABLE employees_employee RENAME COLUMN {old_field_name} TO {new_field_name}"
            with connection.cursor() as cursor:
                cursor.execute(sql)
            return Response({"message": f"Field '{old_field_name}' renamed to '{new_field_name}' successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request):
        """Delete an existing field (column) from the Employee table."""
        field_name = request.data.get('field_name')

        if not field_name:
            return Response({"error": "Field name is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Create a new database cursor
            cursor = connection.cursor()

            # Get existing columns in the table
            cursor.execute("PRAGMA table_info(employees_employee)")
            columns = [column[1] for column in cursor.fetchall()]

            # Check if the specified field exists
            if field_name not in columns:
                return Response({"error": f"Field '{field_name}' not found"}, status=status.HTTP_404_NOT_FOUND)

            # Create new column list excluding the field to be deleted
            new_columns = [col for col in columns if col != field_name]

            # Create a new temporary table without the column to be deleted
            cursor.execute(f"CREATE TABLE employees_employee_temp ({', '.join(new_columns)})")

            # Copy data to the new temporary table excluding the specified column
            cursor.execute(f"INSERT INTO employees_employee_temp ({', '.join(new_columns)}) SELECT {', '.join(new_columns)} FROM employees_employee")

            # Drop the old table
            cursor.execute("DROP TABLE employees_employee")

            # Rename the new table to the original table name
            cursor.execute("ALTER TABLE employees_employee_temp RENAME TO employees_employee")

            return Response({"message": f"Field '{field_name}' deleted successfully"}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    

# class EmployeeDetailView(generics.RetrieveUpdateDestroyAPIView):
#     # serializer_class = EmployeeSerializer  # If you decide to use it later
class EmployeeDetailView(APIView):

    # def get(self, request, pk):
    #     """Retrieve an employee by ID without ORM."""
    #     query = "SELECT * FROM employees_employee WHERE id = %s"
    #     employee = Employee.objects.raw(query, [pk])
    #     if not employee:
    #         return Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)

    #     # Convert employee raw query to dict format
    #     columns = [col[0] for col in connection.cursor().description]
    #     data = {columns[i]: getattr(employee[0], columns[i]) for i in range(len(columns))}

    #     return Response(data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        """Update an employee by ID without ORM."""
        employee_data = request.data
        columns = ', '.join([f"{key} = %s" for key in employee_data.keys()])
        values = list(employee_data.values()) + [pk]

        query = f"UPDATE employees_employee SET {columns} WHERE id = %s"
        
        with connection.cursor() as cursor:
            cursor.execute(query, values)
            if cursor.rowcount == 0:
                return Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)
        
        return Response({"message": "Employee updated successfully"}, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        """Delete an employee by ID without ORM."""
        query = "DELETE FROM employees_employee WHERE id = %s"
        
        with connection.cursor() as cursor:
            cursor.execute(query, ["pk"])
            if cursor.rowcount == 0:
                return Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)
        
        return Response({"message": "Employee deleted successfully"}, status=status.HTTP_204_NO_CONTENT)