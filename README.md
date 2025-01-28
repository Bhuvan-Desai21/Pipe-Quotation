# Raichur Hardware Quotation Generator
A Flask-based web application for generating customized quotations for a hardware business, featuring dynamic pricing, discount management, and PDF generation.

## Features

### Core Functionalities
- **Interactive Pipe Search**: Real-time AJAX-based search with auto-suggestions
- **Cart System**: Add/remove PVC pipes with quantity selection
- **Dynamic Discounts**:
  - Pre-configured discount schemes (GST, Quantity Discounts)
  - Admin interface for discount percentage management
- **Smart Pricing Calculator**:
  - Automatic price calculations with multiple discount stacking
  - GST-compliant pricing (18% included)
- **Professional PDF Generation**:
  - Custom-branded quotations with company details
  - Customer information section
  - Itemized product listing
  - Automatic total calculation
  - Terms & conditions footer

### Technical Features
- **Cloud Database Integration**: SQLite Cloud for real-time data management
- **Secure Configuration**:
  - Environment variable management
  - Protected database credentials
- **Responsive UI**: Mobile-friendly templates
- **Data Validation**: Robust form validation for all inputs

## Technology Stack

- **Backend**: Python Flask
- **Database**: SQLite Cloud
- **PDF Generation**: ReportLab
- **Data Handling**: Pandas
- **Environment Management**: python-dotenv
- **Frontend**: HTML5, CSS3, JavaScript (AJAX)

