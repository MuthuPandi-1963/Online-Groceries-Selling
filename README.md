# Farmer Direct - Farm to Table E-commerce Platform

A Django-based e-commerce platform connecting farmers directly with customers, enabling the sale of fresh produce and agricultural products without intermediaries.

## Features

### For Customers
- Browse fresh products by category
- Real-time stock tracking
- Shopping cart functionality
- Order management
- Secure checkout process

### For Farmers
- Product management (Add, Edit, Delete)
- Inventory tracking
- Order fulfillment
- Sales dashboard
- Status updates for orders

## Technical Stack

- **Backend**: Django 5.1.7
- **Frontend**: Bootstrap 5.3, jQuery
- **Database**: SQLite (default)
- **Image Processing**: Pillow
- **Authentication**: Django built-in auth system

## Prerequisites

- Python 3.12 or higher
- pip (Python package manager)
- Virtual environment (recommended)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/MuthuPandi-1963/Online-Groceries-Selling.git
cd Farmer-app
```

2. Create and activate a virtual environment:
```bash
python -m venv env
source env/bin/activate  # On Windows use: env\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up the database:
```bash
python manage.py migrate
```

5. Create a superuser (admin):
```bash
python manage.py createsuperuser
```

6. Run the development server:
```bash
python manage.py runserver
```

The application will be available at `http://127.0.0.1:8000/`

## Project Structure

```
Farmer-app/
├── manage.py
├── requirements.txt
├── shop/
│   ├── models.py          # Database models
│   ├── views.py           # View logic
│   ├── urls.py            # URL routing
│   ├── forms.py          # Form definitions
│   ├── templatetags/     # Custom template tags
│   └── templates/        # HTML templates
└── static/
    ├── css/              # Custom CSS files
    ├── js/               # JavaScript files
    └── images/           # Static images
```

## Key Models

1. **User**
   - Extended Django's AbstractUser
   - Additional fields for farmer/customer distinction

2. **Product**
   - Name, description, price, stock
   - Category association
   - Image handling
   - Unit management (kg, g, pieces)

3. **Order**
   - UUID-based identification
   - Status tracking
   - Multiple items per order
   - Farmer assignment

## Environment Variables

Create a `.env` file in the project root with these variables:
```
DEBUG=True
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1
```

## Development Guidelines

1. **Code Style**
   - Follow PEP 8 guidelines
   - Use meaningful variable names
   - Add docstrings to functions and classes

2. **Git Workflow**
   - Create feature branches
   - Write descriptive commit messages
   - Test before pushing

3. **Testing**
   - Write unit tests for new features
   - Run tests before committing:
     ```bash
     python manage.py test
     ```

## Common Issues and Solutions

1. **Database Migrations**
   If you encounter migration issues:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

2. **Static Files**
   If static files aren't loading:
   ```bash
   python manage.py collectstatic
   ```

3. **Media Files**
   Ensure media directory exists and has proper permissions:
   ```bash
   mkdir -p media/products
   chmod 755 media/products
   ```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please create an issue in the GitHub repository or contact the maintainers.
