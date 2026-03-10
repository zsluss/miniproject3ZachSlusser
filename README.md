### INF601 - Advanced Programming in Python
### Zach Slusser
### Mini Project 3
 
 
# Recipe Box
 
A Flask web application for storing, sharing, and managing personal recipes with user authentication, database persistence, and a responsive Bootstrap interface.
 
## Description
 
Recipe Box is a full-stack web application built with Flask that allows users to create an account, register, and manage their personal recipe collection. Users can view recipes added by all users, add their own recipes with ingredients and instructions, and delete recipes they have created. The application demonstrates core web development concepts including user authentication with secure password hashing, SQLite database management with foreign key relationships, and Bootstrap-based responsive design with interactive modals.
 
## Getting Started
 
### Dependencies
 
* Python 3.8 or higher
* Windows 10/11 (or macOS/Linux with Python installed)
* pip (Python package manager)
* Virtual environment (venv)
* Flask 2.3.3
* Werkzeug 2.3.7
 
### Installing
 
1. Clone or download the project files to your local machine
2. Navigate to the project directory:
```
cd "c:\Users\[YourUsername]\Documents\1 FHSU\INF601 - Python Advanced\Project_3"
```
3. Create a virtual environment:
```
python -m venv .venv
```
4. Activate the virtual environment (Windows):
```
.venv\Scripts\activate
```
5. Install required packages:
```
pip install -r requirements.txt
```
 
### Executing program
 
1. Initialize the database (first time only):
```
flask --app flaskr init-db
```
2. Run the development server:
```
flask --app flaskr --debug run
```
3. Open your web browser and go to:
```
http://127.0.0.1:5000/
```
4. Register a new account or login
5. Create, view, and manage recipes from the dashboard
 
## Help
 
Common issues and solutions:

**"No module named 'flask'" error**
```
Make sure your virtual environment is activated, then run:
pip install -r requirements.txt
```

**"No such table: users" database error**
```
The database hasn't been initialized. Run:
flask --app flaskr init-db
```

**Port 5000 already in use**
```
Run Flask on a different port:
flask --app flaskr --debug run --port 5001
```

**Changes to code not showing up**
```
Ensure you're running with the --debug flag for auto-reload.
```

 
## Authors
 
**Zach Slusser**
 
## Version History
 
* 1.0
    * Complete Recipe Box application with all rubric requirements
    * User authentication system with secure password hashing
    * SQLite database with users and recipes tables
    * Bootstrap 5 responsive design with delete confirmation modal
    * Full CRUD functionality for recipes with owner protection
* 0.1
    * Initial Release
 
## License
 
This project is created for educational purposes in INF601 - Advanced Programming in Python at Fort Hays State University.
 
## Acknowledgments
 
* [Flask Documentation](https://flask.palletsprojects.com/)
* [Bootstrap 5](https://getbootstrap.com/)
* [Flask Official Tutorial](https://flask.palletsprojects.com/en/2.3.x/tutorial/)
