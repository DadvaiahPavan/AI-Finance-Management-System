# AI Finance Manager 

A modern web application for tracking investments and managing financial portfolios with real-time market data and AI-powered insights.

## Features

### Investment Tracking
- **Real-time Stock Market Data**
  - Live tracking of NSE-listed Indian stocks
  - Dynamic price updates with color-coded indicators
  - Comprehensive stock information (price, change, market cap)
  - AI-powered stock recommendations

- **Cryptocurrency Monitoring**
  - Real-time cryptocurrency price tracking
  - Automatic USD to INR conversion
  - Price change indicators
  - Detailed market information

- **Investment Platform Integration**
  - Comparison of major Indian trading platforms
  - Direct account opening links
  - Platform-specific features and pricing
  - Regulatory compliance information

### User Experience
- **Responsive Design**
  - Mobile-first approach
  - Adaptive layouts for all screen sizes
  - Touch-friendly interface
  - Horizontal scrolling for data tables

- **Interactive Features**
  - Market type toggle (Stocks/Crypto)
  - Manual refresh functionality
  - Persistent view preferences
  - Real-time data updates

## Technical Stack

### Backend
- **Framework**: Flask
- **Database**: SQLAlchemy
- **Authentication**: Flask-Login, Flask-Bcrypt
- **API Integration**: Yahoo Finance via RapidAPI

### Frontend
- **Framework**: Bootstrap 5.1.3
- **Icons**: Font Awesome
- **Styling**: Custom CSS with responsive design
- **JavaScript**: Vanilla JS with modern ES6+ features

## Installation

1. Clone the repository:
```bash
git clone https://github.com/DadvaiahPavan/AI-Finance-Management-System.git
cd Finance
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

5. Initialize the database:
```bash
flask db upgrade
```

6. Run the application:
```bash
python app.py
```

## Environment Variables

Create a `.env` file with the following variables:
```env
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your_secret_key
RAPIDAPI_KEY=your_rapidapi_key
DATABASE_URL=sqlite:///finance.db
```

## API Documentation

### Yahoo Finance API (via RapidAPI)
- **Endpoint**: Yahoo Finance API
- **Rate Limits**: As per RapidAPI plan
- **Authentication**: API key required
- **Data Points**:
  - Real-time stock prices
  - Company information
  - Market statistics
  - Historical data

## Security Features

- Secure password hashing with Flask-Bcrypt
- Session management with Flask-Login
- Environment-based configuration
- CSRF protection
- Secure API key handling

## Future Enhancements

1. **Analytics**
   - Portfolio performance tracking
   - Risk analysis
   - Investment recommendations
   - Historical performance charts

2. **User Features**
   - Custom watchlists
   - Price alerts
   - Portfolio sharing
   - Export functionality

3. **Technical**
   - Real-time WebSocket updates
   - Enhanced error handling
   - Caching implementation
   - Mobile app development

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Yahoo Finance API](https://rapidapi.com/apidojo/api/yahoo-finance1)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Bootstrap Documentation](https://getbootstrap.com/docs/5.1)
- Indian Trading Platforms:
  - [Zerodha](https://zerodha.com)
  - [Groww](https://groww.in)
  - [Upstox](https://upstox.com)

---
Made with by Pavan Dadvaiah 
