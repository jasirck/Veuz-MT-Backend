
# Veuz MT Backend

This project is a Django backend application that supports a user signup page, an employee module, and dynamic field management for employee details.

## Requirements

Make sure you have the following installed:
- Python 3.x
- pip

## Installation Steps

1. **Create a Virtual Environment and Activate it**

   Navigate to the desired directory and create a virtual environment:
   ```bash
   python -m venv env
   ```
   Activate the virtual environment:
   - On Windows:
     ```bash
     .\env\Scripts ctivate
     ```
   - On macOS/Linux:
     ```bash
     source env/bin/activate
     ```

2. **Clone the Repository**

   Create a folder for the project and enter it:
   ```bash
   mkdir Veuz-MT-Backend
   cd Veuz-MT-Backend
   ```
   Clone the repository:
   ```bash
   git clone https://github.com/jasirck/Veuz-MT-Backend.git
   cd Veuz-MT-Backend
   ```

3. **Install Required Packages**

   Install the required packages using pip:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run Migrations**

   Make migrations and migrate the database:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Run the Development Server**

   Start the Django development server:
   ```bash
   python manage.py runserver
   ```

Now, you can access the application at `http://127.0.0.1:8000/`.

## Features

- **Signup Page**: Users can create accounts with name, email, and password. 
- **Dashboard**: Upon successful signup, users are redirected to the dashboard.
- **Employee Module**: View a list of employees with search functionality and a modal to add employee details.
- **Dynamic Field Management**: Manage employee fields dynamically through the settings section.

