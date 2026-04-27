### INF601 - Advanced Programming in Python
### Zach Slusser
### Final Project
 
 
# Recipe Box
 
A Flask web application for storing, sharing, and managing personal recipes with user authentication.
 
## Description
 
Recipe Box is a full‑stack web app I built with Flask that lets users create an account and keep track of their own recipes. You can browse recipes from everyone, add your own with ingredients and instructions, and remove anything you’ve posted. Building it gave me a chance to work with core web development concepts like secure user authentication, SQLite with proper foreign key relationships, and a responsive Bootstrap layout with interactive components.
The primary use for this is to run it on a local server for your family to share recipes on. It will show all of the recipes that your family adds to it but allows you to pull up just yours if you are trying to find something specific. I'd like to also add a grocery option to this as well.
 
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
2. Navigate to the project directory
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
6. If you are wanting to run this on a home server that can be accessed by all phones or computers on the network then you need to run
'''
flask --app flaskr --debug run --host 0.0.0.0 --port 5000
'''

 
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

**Accessing the app from another device on your LAN**
```
Start Flask so it listens on your network interface:
flask --app flaskr --debug run --host 0.0.0.0 --port 5000

Then open it from another device using your computer's local IP:
http://<your-local-ip>:5000/

Example:
http://192.168.1.42:5000/

If it still does not load, allow Python/Flask through Windows Firewall
for Private networks.
```

**Changes to code not showing up**
```
Ensure you're running with the --debug flag for auto-reload.
```

 
## Authors
 
**Zach Slusser**
 
## Version History
 
* 1.1
    * Added favorites feature with star indicators on recipe cards
    * Favorite recipes automatically appear at the top of recipe lists
    * One-click favorite/unfavorite toggle button on recipe cards and detail pages
    * Favorites persist across sessions for logged-in users
    * New favorites table in database tracking user-recipe relationships

* 1.0
    * Complete Recipe Box application with all rubric requirements
    * User authentication system with secure password hashing
    * SQLite database with users and recipes tables
    * Bootstrap 5 responsive design with delete confirmation modal
    * Full CRUD functionality for recipes with owner protection
    * TheMealDB API integration for meal discovery
    * Category filtering for random meal lookup
    * Recipe search by title and ingredients
    * Source URL support for external recipe links

 
## License
 
This project is created for educational purposes in INF601 - Advanced Programming in Python at Fort Hays State University.
 
## Acknowledgments
 
* [Flask Documentation](https://flask.palletsprojects.com/)
* [Bootstrap 5](https://getbootstrap.com/)
* [Flask Official Tutorial](https://flask.palletsprojects.com/en/2.3.x/tutorial/)
