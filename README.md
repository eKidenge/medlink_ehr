# MedLink EHR - Electronic Health Record System

![MedLink EHR](https://img.shields.io/badge/MedLink-EHR-blue?style=for-the-badge&logo=healthcare)
![Django](https://img.shields.io/badge/Django-6.0-green?style=flat&logo=django)
![Python](https://img.shields.io/badge/Python-3.14-blue?style=flat&logo=python)
![License](https://img.shields.io/badge/License-Proprietary-red?style=flat)

## Overview

MedLink EHR is a comprehensive Electronic Health Record system designed specifically for Kenyan healthcare facilities. It provides a complete solution for managing patient records, appointments, laboratory results, pharmacy inventory, and hospital administration with role-based access control.

### Key Features

- Role-Based Access Control - Super Admin, Admin, Doctor, Nurse, Lab Technician, Pharmacist, Receptionist, Cashier, and Viewer roles
- Patient Management - Complete patient records, medical history, and treatment plans
- Appointment Scheduling - Manage patient appointments with real-time availability
- Triage System - Quick patient assessment and priority classification
- Laboratory Integration - Lab request management and digital results tracking
- Pharmacy Management - Inventory tracking, prescription management, and stock alerts
- Admissions Management - Bed allocation and patient admission tracking
- Reporting and Analytics - Real-time dashboards and comprehensive reports
- Audit Logging - Complete system activity tracking
- Two-Factor Authentication - Enhanced security for user accounts
- Notifications System - Real-time user notifications

## Table of Contents

- [Technology Stack](#technology-stack)
- [Installation](#installation)
- [Configuration](#configuration)
- [Database Setup](#database-setup)
- [Running the Application](#running-the-application)
- [System Architecture](#system-architecture)
- [User Roles](#user-roles)
- [Role Flow Diagrams](#role-flow-diagrams)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [Security Features](#security-features)
- [Testing](#testing)
- [Performance Optimization](#performance-optimization)
- [Troubleshooting](#troubleshooting)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)
- [Contact and Support](#contact-and-support)
- [Additional Resources](#additional-resources)

## Technology Stack

### Backend

- Django 6.0 - Python web framework
- Django REST Framework - API development
- Simple JWT - JSON Web Token authentication
- SQLite / PostgreSQL - Database
- Celery - Asynchronous task queue
- Redis - Caching and message broker

### Frontend

- Tailwind CSS - Utility-first CSS framework
- Chart.js - Interactive charts and graphs
- Font Awesome - Icon library
- FullCalendar - Appointment management

### Development Tools

- Git - Version control
- pip - Package management
- Virtual Environment - Isolated Python environment

## Installation

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- Virtual environment tool (venv)

### Step 1: Clone the Repository

```bash
git clone https://github.com/eKidenge/medlink-ehr.git
cd medlink-ehr
```

### Step 2: Create and Activate Virtual Environment

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Environment Variables

Create a `.env` file in the root directory:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3

# Email Configuration (Optional)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-password
DEFAULT_FROM_EMAIL=noreply@medlink.co.ke

# JWT Settings
JWT_ACCESS_TOKEN_LIFETIME=60
JWT_REFRESH_TOKEN_LIFETIME=1440
```

## Configuration

### Settings Configuration

Create `medlink_ehr/settings_local.py` for local settings (optional):

```python
from .settings import *

DEBUG = True
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

### Email Configuration

For email functionality, configure in `settings.py`:

```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
DEFAULT_FROM_EMAIL = 'noreply@medlink.co.ke'
```

## Database Setup

### Apply Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### Create Superuser

```bash
python manage.py createsuperuser
```

Follow the prompts to create an administrator account.

### Load Initial Data

```bash
python manage.py loaddata fixtures/initial_data.json
```

## Running the Application

### Development Server

```bash
python manage.py runserver
```

The application will be available at: http://127.0.0.1:8000/

### Access the Application

| URL | Description |
|---|---|
| `/` | Landing Page |
| `/login/` | Login Page |
| `/register/` | Registration Page |
| `/dashboard/` | User Dashboard |
| `/dashboard/admin/` | Admin Dashboard |
| `/api/` | API Root |
| `/swagger/` | API Documentation |
| `/admin/` | Django Admin Panel |

## System Architecture

```mermaid
flowchart TD
    START([User Visits MedLink EHR]) --> LAND[Landing Page]
    LAND --> CHOICE{Has Account?}

    CHOICE -- No --> REG[Registration]
    CHOICE -- Yes --> LOGIN[Login]

    REG --> VERIFY[Email / 2FA Verification]
    VERIFY --> LOGIN

    LOGIN --> AUTH{Credentials Valid?}
    AUTH -- No --> LOGIN
    AUTH -- Yes --> TWOFA{2FA Enabled?}
    TWOFA -- Yes --> OTP[Enter 2FA Code]
    TWOFA -- No --> ROLE{Role?}
    OTP --> ROLE

    ROLE -- Super Admin --> SA[Super Admin Dashboard]
    ROLE -- Admin --> AD[Admin Dashboard]
    ROLE -- Doctor --> DR[Doctor Dashboard]
    ROLE -- Nurse --> NU[Nurse Dashboard]
    ROLE -- Lab Technician --> LT[Lab Dashboard]
    ROLE -- Pharmacist --> PH[Pharmacy Dashboard]
    ROLE -- Receptionist --> RE[Reception Dashboard]
    ROLE -- Cashier --> CA[Cashier Dashboard]
    ROLE -- Manager --> MA[Manager Dashboard]
    ROLE -- Viewer --> VI[Viewer Dashboard]

    SA --> CORE[(Core Modules)]
    AD --> CORE
    DR --> CORE
    NU --> CORE
    LT --> CORE
    PH --> CORE
    RE --> CORE
    CA --> CORE
    MA --> CORE
    VI --> CORE

    CORE --> M1[Patients]
    CORE --> M2[Appointments]
    CORE --> M3[Triage]
    CORE --> M4[Laboratory]
    CORE --> M5[Pharmacy]
    CORE --> M6[Admissions]
    CORE --> M7[Reports]
    CORE --> M8[Audit Logs]
    CORE --> M9[Notifications]

    classDef entry fill:#4A90E2,stroke:#1F3A5F,color:#fff
    classDef auth fill:#7ED321,stroke:#3B6B00,color:#fff
    classDef role fill:#9013FE,stroke:#4A0A85,color:#fff
    classDef core fill:#D0021B,stroke:#6B000D,color:#fff
    class START,LAND,CHOICE entry
    class REG,LOGIN,VERIFY,AUTH,TWOFA,OTP auth
    class SA,AD,DR,NU,LT,PH,RE,CA,MA,VI,ROLE role
    class CORE,M1,M2,M3,M4,M5,M6,M7,M8,M9 core
```

## User Roles

| Role | Dashboard URL | Permissions |
|---|---|---|
| Super Admin | `/dashboard/admin/` | Full system access, user management, settings |
| Admin | `/dashboard/admin/` | Full system access, user management |
| Doctor | `/dashboard/doctor/` | Patient management, prescriptions, lab requests |
| Nurse | `/dashboard/nurse/` | Triage, vital signs, patient care |
| Lab Technician | `/dashboard/lab/` | Lab tests, results entry, equipment management |
| Pharmacist | `/dashboard/pharmacy/` | Prescription dispensing, inventory management |
| Receptionist | `/dashboard/reception/` | Patient registration, appointments |
| Cashier | `/dashboard/cashier/` | Payment processing, invoices |
| Manager | `/dashboard/manager/` | Staff management, reports |
| Viewer | `/dashboard/viewer/` | Read-only access |

## Role Flow Diagrams

### Registration and Login Flow

```mermaid
flowchart TD
    A([Start]) --> B{Has Account?}

    B -- No --> C[Registration Form]
    C --> D[Name, Email, Password, Role]
    D --> E{Valid Input?}
    E -- No --> F[Show Errors] --> C
    E -- Yes --> G[Create User Account]
    G --> H[Send Verification Email]
    H --> I{Verified?}
    I -- No --> J[Resend Verification] --> H
    I -- Yes --> K[Login Page]

    B -- Yes --> K
    K --> L[Enter Credentials]
    L --> M{Valid?}
    M -- No --> N[Invalid Credentials] --> K
    M -- Yes --> O{2FA Enabled?}
    O -- No --> P{Role?}
    O -- Yes --> Q[Enter 2FA Code]
    Q --> R{Code Valid?}
    R -- No --> K
    R -- Yes --> P

    P -- Super Admin --> S1[Super Admin Dashboard]
    P -- Admin --> S2[Admin Dashboard]
    P -- Doctor --> S3[Doctor Dashboard]
    P -- Nurse --> S4[Nurse Dashboard]
    P -- Lab Technician --> S5[Lab Dashboard]
    P -- Pharmacist --> S6[Pharmacy Dashboard]
    P -- Receptionist --> S7[Reception Dashboard]
    P -- Cashier --> S8[Cashier Dashboard]
    P -- Manager --> S9[Manager Dashboard]
    P -- Viewer --> S10[Viewer Dashboard]

    classDef reg fill:#F5A623,stroke:#8B5A00,color:#fff
    classDef auth fill:#7ED321,stroke:#3B6B00,color:#fff
    classDef role fill:#9013FE,stroke:#4A0A85,color:#fff
    class C,D,E,F,G,H,I,J reg
    class K,L,M,N,O,Q,R auth
    class P,S1,S2,S3,S4,S5,S6,S7,S8,S9,S10 role
```

### Super Admin and Admin Flow

```mermaid
flowchart TD
    A[Admin Dashboard] --> B[User Management]
    A --> C[Role Management]
    A --> D[System Settings]
    A --> E[Audit Logs]
    A --> F[Reports and Analytics]
    A --> G[Notifications]

    B --> B1[Create User]
    B --> B2[Edit User]
    B --> B3[Suspend User]
    B --> B4[Reset Password]

    C --> C1[Assign Roles]
    C --> C2[Define Permissions]

    D --> D1[General Settings]
    D --> D2[Email Configuration]
    D --> D3[Security Policies]

    E --> E1[View Activity Logs]
    E --> E2[Export Logs]

    F --> F1[User Reports]
    F --> F2[System Reports]
    F --> F3[Financial Reports]

    classDef admin fill:#D0021B,stroke:#6B000D,color:#fff
    class A,B,C,D,E,F,G,B1,B2,B3,B4,C1,C2,D1,D2,D3,E1,E2,F1,F2,F3 admin
```

### Doctor Flow

```mermaid
flowchart TD
    A[Doctor Dashboard] --> B[My Appointments]
    A --> C[Patient Records]
    A --> D[Prescriptions]
    A --> E[Lab Requests]
    A --> F[Admissions]

    B --> B1[View Today Schedule]
    B --> B2[Start Consultation]
    B --> B3[Complete Appointment]

    C --> C1[Search Patient]
    C --> C2[View Medical History]
    C --> C3[Add Diagnosis]
    C --> C4[Update Treatment Plan]

    D --> D1[Create Prescription]
    D --> D2[Send to Pharmacy]
    D --> D3[View Prescription History]

    E --> E1[Request Lab Test]
    E --> E2[View Lab Results]
    E --> E3[Review Critical Results]

    F --> F1[Admit Patient]
    F --> F2[Update Admission Status]
    F --> F3[Discharge Patient]

    classDef doctor fill:#4A90E2,stroke:#1F3A5F,color:#fff
    class A,B,C,D,E,F,B1,B2,B3,C1,C2,C3,C4,D1,D2,D3,E1,E2,E3,F1,F2,F3 doctor
```

### Nurse Flow

```mermaid
flowchart TD
    A[Nurse Dashboard] --> B[Triage Queue]
    A --> C[Vital Signs]
    A --> D[Patient Care]
    A --> E[Appointments]

    B --> B1[Assess Patient]
    B --> B2[Assign Priority]
    B --> B3[Send to Doctor]

    C --> C1[Record Vitals]
    C --> C2[Update Patient Chart]

    D --> D1[Administer Medication]
    D --> D2[Update Care Notes]
    D --> D3[Monitor Patients]

    E --> E1[View Schedule]
    E --> E2[Check-in Patient]

    classDef nurse fill:#50E3C2,stroke:#1F7A66,color:#000
    class A,B,C,D,E,B1,B2,B3,C1,C2,D1,D2,D3,E1,E2 nurse
```

### Lab Technician Flow

```mermaid
flowchart TD
    A[Lab Dashboard] --> B[Lab Requests]
    A --> C[Test Results]
    A --> D[Equipment]
    A --> E[Inventory]

    B --> B1[View Pending Requests]
    B --> B2[Accept Request]
    B --> B3[Collect Sample]

    C --> C1[Enter Results]
    C --> C2[Flag Abnormal Values]
    C --> C3[Notify Doctor]

    D --> D1[Equipment Status]
    D --> D2[Maintenance Log]

    E --> E1[Reagent Stock]
    E --> E2[Reorder Alerts]

    classDef lab fill:#F5A623,stroke:#8B5A00,color:#fff
    class A,B,C,D,E,B1,B2,B3,C1,C2,C3,D1,D2,E1,E2 lab
```

### Pharmacist Flow

```mermaid
flowchart TD
    A[Pharmacy Dashboard] --> B[Prescriptions]
    A --> C[Inventory]
    A --> D[Stock Alerts]
    A --> E[Dispensing]

    B --> B1[View Pending Prescriptions]
    B --> B2[Verify Prescription]
    B --> B3[Prepare Medication]

    C --> C1[View Stock Levels]
    C --> C2[Add New Stock]
    C --> C3[Update Prices]

    D --> D1[Low Stock Alerts]
    D --> D2[Expiry Alerts]
    D --> D3[Reorder Requests]

    E --> E1[Dispense to Patient]
    E --> E2[Update Records]
    E --> E3[Print Label]

    classDef pharm fill:#9013FE,stroke:#4A0A85,color:#fff
    class A,B,C,D,E,B1,B2,B3,C1,C2,C3,D1,D2,D3,E1,E2,E3 pharm
```

### Receptionist Flow

```mermaid
flowchart TD
    A[Reception Dashboard] --> B[Patient Registration]
    A --> C[Appointments]
    A --> D[Check-in]
    A --> E[Inquiries]

    B --> B1[New Patient]
    B --> B2[Search Existing]
    B --> B3[Update Details]

    C --> C1[Book Appointment]
    C --> C2[Reschedule]
    C --> C3[Cancel]

    D --> D1[Check-in Patient]
    D --> D2[Direct to Triage]

    E --> E1[Answer Queries]
    E --> E2[Direct to Department]

    classDef rec fill:#B8E986,stroke:#4A7A1F,color:#000
    class A,B,C,D,E,B1,B2,B3,C1,C2,C3,D1,D2,E1,E2 rec
```

### Cashier Flow

```mermaid
flowchart TD
    A[Cashier Dashboard] --> B[Invoices]
    A --> C[Payments]
    A --> D[Reports]

    B --> B1[Generate Invoice]
    B --> B2[View Pending Invoices]
    B --> B3[Print Invoice]

    C --> C1[Process Payment]
    C --> C2[Cash / M-PESA / Card]
    C --> C3[Issue Receipt]

    D --> D1[Daily Collection]
    D --> D2[Payment History]
    D --> D3[Export Report]

    classDef cash fill:#E0E0E0,stroke:#666,color:#000
    class A,B,C,D,B1,B2,B3,C1,C2,C3,D1,D2,D3 cash
```

### Manager Flow

```mermaid
flowchart TD
    A[Manager Dashboard] --> B[Staff Management]
    A --> C[Reports]
    A --> D[Analytics]
    A --> E[Operations]

    B --> B1[View Staff]
    B --> B2[Assign Shifts]
    B --> B3[Performance]

    C --> C1[Patient Reports]
    C --> C2[Financial Reports]
    C --> C3[Department Reports]

    D --> D1[KPIs]
    D --> D2[Trends]
    D --> D3[Forecasts]

    E --> E1[Bed Occupancy]
    E --> E2[Resource Allocation]
    E --> E3[Compliance]

    classDef mgr fill:#F8E71C,stroke:#8B7D00,color:#000
    class A,B,C,D,E,B1,B2,B3,C1,C2,C3,D1,D2,D3,E1,E2,E3 mgr
```

### Viewer Flow

```mermaid
flowchart TD
    A[Viewer Dashboard] --> B[Read-Only Access]
    B --> C[View Reports]
    B --> D[View Dashboards]
    B --> E[View Patient Summary]

    C --> C1[Non-Editable Reports]
    D --> D1[Statistics Only]
    E --> E1[Limited Patient Info]

    classDef viewer fill:#E0E0E0,stroke:#666,color:#000
    class A,B,C,D,E,C1,D1,E1 viewer
```

### Patient Lifecycle

```mermaid
sequenceDiagram
    participant P as Patient
    participant R as Receptionist
    participant N as Nurse
    participant D as Doctor
    participant L as Lab
    participant PH as Pharmacy
    participant C as Cashier

    P->>R: Arrive / Register
    R->>R: Create Patient Record
    R->>N: Send to Triage
    N->>N: Record Vitals and Priority
    N->>D: Assign to Doctor
    D->>D: Consultation and Diagnosis
    D->>L: Request Lab Tests
    L->>L: Process Samples
    L->>D: Return Results
    D->>PH: Issue Prescription
    PH->>P: Dispense Medication
    D->>C: Generate Bill
    C->>P: Process Payment
    C->>P: Issue Receipt
```

### Permission Matrix

```mermaid
flowchart LR
    subgraph Roles
        SA[Super Admin]
        AD[Admin]
        DR[Doctor]
        NU[Nurse]
        LT[Lab]
        PH[Pharmacy]
        RE[Reception]
        CA[Cashier]
        MA[Manager]
        VI[Viewer]
    end

    subgraph Permissions
        P1[Manage Users]
        P2[Manage System]
        P3[Patient Records]
        P4[Prescriptions]
        P5[Lab Requests]
        P6[Dispense Meds]
        P7[Register Patients]
        P8[Process Payments]
        P9[View Reports]
        P10[Read Only]
    end

    SA --> P1 & P2 & P3 & P4 & P5 & P6 & P7 & P8 & P9
    AD --> P1 & P2 & P3 & P4 & P5 & P6 & P7 & P8 & P9
    DR --> P3 & P4 & P5 & P9
    NU --> P3 & P7
    LT --> P5 & P9
    PH --> P4 & P6
    RE --> P7
    CA --> P8
    MA --> P9
    VI --> P10
```

## API Documentation

### Authentication Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/accounts/auth/login/` | User login with JWT |
| POST | `/api/accounts/auth/register/` | User registration |
| POST | `/api/accounts/auth/logout/` | User logout |
| POST | `/api/accounts/auth/verify-2fa/` | Verify 2FA code |
| POST | `/api/token/refresh/` | Refresh JWT token |
| POST | `/api/token/verify/` | Verify JWT token |

### User Management Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/accounts/users/` | List all users |
| GET | `/api/accounts/users/{id}/` | Get user details |
| POST | `/api/accounts/users/` | Create user |
| PUT | `/api/accounts/users/{id}/` | Update user |
| DELETE | `/api/accounts/users/{id}/` | Delete user |

### Dashboard Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/dashboard/stats/` | Dashboard statistics |
| GET | `/api/dashboard/kpis/` | Key performance indicators |
| GET | `/api/dashboard/activity/` | Recent activity feed |
| GET | `/api/dashboard/notifications/unread/` | Unread notifications |

### Patient Management Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/patients/` | List patients |
| POST | `/api/patients/` | Create patient |
| GET | `/api/patients/{id}/` | Get patient details |
| PUT | `/api/patients/{id}/` | Update patient |

### Authentication Required

All API endpoints except `/api/accounts/auth/login/`, `/api/accounts/auth/register/`, `/api/token/refresh/`, and `/api/token/verify/` require JWT authentication.

Headers:

```
Authorization: Bearer <access_token>
```

## Project Structure

```
medlink_ehr/
├── apps/
│   ├── accounts/
│   │   ├── migrations/
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   └── permissions.py
│   ├── dashboard/
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── serializers.py
│   ├── patients/
│   │   ├── models.py
│   │   ├── views.py
│   │   └── serializers.py
│   ├── visits/
│   │   ├── models.py
│   │   └── views.py
│   └── reports/
│       ├── models.py
│       └── views.py
├── templates/
│   ├── dashboard/
│   │   ├── base_dashboard.html
│   │   ├── index.html
│   │   ├── admin_dashboard.html
│   │   ├── doctor_dashboard.html
│   │   └── viewer_dashboard.html
│   ├── index.html
│   ├── login.html
│   └── register.html
├── static/
│   ├── css/
│   ├── js/
│   └── images/
├── medlink_ehr/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── manage.py
├── requirements.txt
└── README.md
```

## Security Features

- JWT Authentication - Secure token-based authentication
- Two-Factor Authentication - Optional 2FA for enhanced security
- Role-Based Access Control - Granular permissions per role
- Session Management - Track and terminate user sessions
- Audit Logging - Complete system activity tracking
- Password Policies - Strong password requirements
- Account Lockout - Automatic lockout after failed attempts
- CSRF Protection - Cross-site request forgery protection
- SQL Injection Prevention - ORM-based queries
- XSS Protection - Escaped template variables

## Testing

### Run Tests

```bash
python manage.py test
```

### Run Specific Test

```bash
python manage.py test apps.accounts.tests
```

### Test Coverage

```bash
coverage run manage.py test
coverage report
```

## Performance Optimization

- Database Indexing - Optimized queries with indexes
- Caching - Redis caching for frequent queries
- Query Optimization - Select related and prefetch related
- Static Files - Compressed and minified assets
- CDN - Content delivery network for static files

## Troubleshooting

### Common Issues

1. Database Migration Errors

```bash
python manage.py makemigrations --merge
python manage.py migrate
```

2. Static Files Not Loading

```bash
python manage.py collectstatic --no-input
```

3. Email Not Sending

Check email configuration in `settings.py` and ensure credentials are correct.

4. Permission Issues

```bash
chmod -R 755 media/
chmod -R 755 static/
```

### Development Logs

Logs are stored in:

```
logs/
├── debug.log
├── error.log
└── access.log
```

## Deployment

### Production Checklist

- Set `DEBUG=False` in settings
- Configure proper `ALLOWED_HOSTS`
- Set up SSL certificate
- Configure production database (PostgreSQL recommended)
- Set up email backend
- Configure CDN for static files
- Set up logging and monitoring
- Regular backups
- Security audit

### Deployment Options

#### Option 1: Heroku

```bash
heroku create medlink-ehr
git push heroku main
heroku run python manage.py migrate
```

#### Option 2: AWS EC2

```bash
ssh -i key.pem ec2-user@ec2-ip-address
sudo apt update
sudo apt install nginx postgresql
# Configure and deploy
```

#### Option 3: Docker

```bash
docker build -t medlink-ehr .
docker run -d -p 8000:8000 medlink-ehr
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Coding Standards

- Follow PEP 8 style guide
- Write unit tests for new features
- Update documentation accordingly
- Use meaningful commit messages

## License

This project is proprietary and confidential. Unauthorized copying, distribution, or use is strictly prohibited.

## Contact and Support

| Type | Contact |
|---|---|
| Email | support@medlink.co.ke |
| Phone | +254 700 123 456 |
| Website | https://medlink.co.ke |
| Address | Westlands, Nairobi, Kenya |

## Additional Resources

- Django Documentation - https://docs.djangoproject.com/
- Django REST Framework - https://www.django-rest-framework.org/
- Tailwind CSS - https://tailwindcss.com/
- Chart.js - https://www.chartjs.org/

MedLink EHR 2026 - Revolutionizing Healthcare Delivery in Kenya