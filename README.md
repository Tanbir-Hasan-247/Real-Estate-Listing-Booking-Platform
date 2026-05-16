# PropNest - Real Estate Listing & Booking Platform 🏡

PropNest is a comprehensive, multi-role real estate platform built with Django. It allows users to buy, sell, or rent properties, schedule property tours, and interact with real estate agents. The platform features a role-based dashboard for Buyers, Agents, and Administrators.

## 🚀 Key Features

### 👤 User Roles & Authentication
* **Custom User Model:** Built-in roles for `Admin`, `Agent`, and `Buyer`.
* **Secure Authentication:** Registration, Login, Logout, and Account Activation via Email.

### 🏢 Property Management (Agents)
* **CRUD Operations:** Agents can add, edit, and delete their property listings.
* **Multiple Image Uploads:** Attach multiple images to a single property.
* **Agent Dashboard:** Monitor active listings, total properties, and incoming tour requests.

### 🔍 Explore & Search (Buyers)
* **Advanced Filters:** Search by keyword, listing type (rent/sale), property type, bedrooms, and price range.
* **Wishlist (Saved Properties):** Buyers can save their favorite properties for later viewing.
* **Tour Booking:** Schedule in-person property tours directly from the property details page.

### 🛡️ Admin Controls (Administrators)
* **Platform Overview:** Global dashboard to manage all properties, users, and platform activity.
* **User & Agent Management:** View, edit, suspend, or delete users and agents.
* **Global Tour Management:** Admins can intervene and update tour request statuses on behalf of agents.

### ✉️ Automated Notifications
* **Email Alerts:** Automated emails sent to buyers when a tour request is Confirmed, Cancelled, or Completed using **Django Signals**.

---

## 🛠️ Tech Stack

* **Backend:** Python, Django 6.0.3
* **Database:** PostgreSQL
* **Frontend:** Tailwind CSS, Bootstrap 5, HTML5, FontAwesome
* **Others:** Django Signals, default_token_generator (for email verification)

---

## 📸 Screenshots

*(Replace the placeholder links with your actual image paths once you take screenshots)*

### Home Page
![Home Page](media/screenshots/home_page.png)

### Property Details & Tour Booking
![Property Details](media/screenshots/property_details.png)

### Agent Dashboard
![Agent Dashboard](media/screenshots/agent_dashboard.png)

### Admin Platform Overview
![Admin Dashboard](media/screenshots/admin_dashboard.png)

---

## 🚧 Upcoming Updates (Roadmap)

- [ ] **Refactoring to Class-Based Views (CBV):** Transitioning existing Function-Based Views (FBV) to Django's Class-Based Views for cleaner, more scalable, and maintainable code.
- [ ] **Payment Gateway Integration:** For premium agent listings or booking fees.
- [ ] **Map Integration:** Interactive Google Maps for property locations.

---

## ⚙️ Installation & Setup

Follow these steps to run the project locally on your machine.

### 1. Clone the repository
```bash
git clone [https://github.com/your-username/Real-Estate-Listing-Booking-Platform.git](https://github.com/your-username/Real-Estate-Listing-Booking-Platform.git)
cd Real-Estate-Listing-Booking-Platform
```

### 2. Create and activate a virtual environment
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup Environment Variables
Create a .env file in the root directory and configure your database and email settings:

```Code snipet
SECRET_KEY=your_django_secret_key
DB_NAME=your_db_name
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432

EMAIL_HOST=smtp.gmail.com
EMAIL_USE_TLS=True
EMAIL_PORT=587
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
```

### 5. Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Populate Fake Data (Optional but recommended)
You can use the provided script to generate fake properties, agents, and categories.
```bash
python populateDB.py
```

### 7. Create a Superuser (Admin)
```bash
python manage.py createsuperuser
```

### 8. Run the Development Server
```bash
python manage.py runserver
```
Visit http://127.0.0.1:8000/ in your browser to explore the platform.

## 👨‍💻 Author

**Tanbir Hasan**  
Aspiring Software Developer & Competitive Programmer  

GitHub: https://github.com/Tanbir-Hasan-247