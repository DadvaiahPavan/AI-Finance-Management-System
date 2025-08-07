from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import requests
import pandas as pd
import time
import json
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY", "fa3e1e5c9b7244b6b8c42064d57bdb35f50d39d64ae6b9c3e7d4c1b72de8d4a6"
)

# Database configuration - handle both local and production
database_url = os.getenv("DATABASE_URL", "sqlite:///finance.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize extensions
db = SQLAlchemy()
db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# User Model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    transactions = db.relationship("Transaction", backref="user", lazy=True)

# Transaction Model
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # "income" or "expense"
    description = db.Column(db.String(200))
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Initialize database
def init_db():
    """Initialize database tables"""
    try:
        with app.app_context():
            db.create_all()
            print("✅ Database tables created successfully")
            return True
    except Exception as e:
        print(f"❌ Error creating database tables: {str(e)}")
        return False


# Routes
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        try:
            username = request.form.get("username")
            password = request.form.get("password")

            if not username or not password:
                flash("Please provide both username and password", "error")
                return render_template("login.html")

            user = User.query.filter_by(username=username).first()

            if user and bcrypt.check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for("dashboard"))
            else:
                flash("Invalid username or password", "error")
        except Exception as e:
            print(f"Login error: {str(e)}")
            flash("An error occurred during login. Please try again.", "error")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        try:
            username = request.form.get("username")
            email = request.form.get("email")
            password = request.form.get("password")

            if not username or not email or not password:
                flash("Please fill in all fields", "error")
                return render_template("register.html")

            # Check if user already exists
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash("Username already exists", "error")
                return render_template("register.html")

            existing_email = User.query.filter_by(email=email).first()
            if existing_email:
                flash("Email already registered", "error")
                return render_template("register.html")

            # Create new user
            hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
            user = User(username=username, email=email, password=hashed_password)
            db.session.add(user)
            db.session.commit()

            flash("Registration successful! Please login.", "success")
            return redirect(url_for("login"))

        except Exception as e:
            print(f"Registration error: {str(e)}")
            db.session.rollback()
            flash("An error occurred during registration. Please try again.", "error")

    return render_template("register.html")


@app.route("/dashboard")
@login_required
def dashboard():
    try:
        transactions = (
            Transaction.query.filter_by(user_id=current_user.id)
            .order_by(Transaction.date.desc())
            .all()
        )

        # Calculate financial summary
        total_income = sum(t.amount for t in transactions if t.transaction_type == "income")
        total_expenses = sum(t.amount for t in transactions if t.transaction_type == "expense")
        balance = total_income - total_expenses

        # Get monthly summary
        current_month = datetime.utcnow().month
        monthly_transactions = [t for t in transactions if t.date.month == current_month]
        monthly_income = sum(t.amount for t in monthly_transactions if t.transaction_type == "income")
        monthly_expenses = sum(t.amount for t in monthly_transactions if t.transaction_type == "expense")

        return render_template(
            "dashboard.html",
            transactions=transactions,
            total_income=total_income,
            total_expenses=total_expenses,
            balance=balance,
            monthly_income=monthly_income,
            monthly_expenses=monthly_expenses,
        )
    except Exception as e:
        print(f"Dashboard error: {str(e)}")
        flash("An error occurred loading the dashboard", "error")
        return render_template(
            "dashboard.html",
            transactions=[],
            total_income=0,
            total_expenses=0,
            balance=0,
            monthly_income=0,
            monthly_expenses=0,
        )


@app.route("/add_transaction", methods=["POST"])
@login_required
def add_transaction():
    try:
        amount = float(request.form.get("amount"))
        category = request.form.get("category")
        transaction_type = request.form.get("transaction_type")
        description = request.form.get("description")

        transaction = Transaction(
            amount=amount,
            category=category,
            transaction_type=transaction_type,
            description=description,
            user_id=current_user.id,
        )

        db.session.add(transaction)
        db.session.commit()

        # Get updated transaction count for spending patterns
        transaction_count = Transaction.query.filter_by(user_id=current_user.id).count()

        if transaction_count >= 5:
            # Analyze spending patterns
            transactions = Transaction.query.filter_by(user_id=current_user.id).all()
            spending_data = {}
            for t in transactions:
                if t.transaction_type == "expense":
                    if t.category not in spending_data:
                        spending_data[t.category] = 0
                    spending_data[t.category] += t.amount

            # Find top spending categories
            sorted_spending = (
                sorted(spending_data.items(), key=lambda x: x[1], reverse=True)
            )
            top_categories = (
                sorted_spending[:3] if len(sorted_spending) >= 3 else sorted_spending
            )

            # Generate spending insights
            if top_categories:
                insights = f"Top spending categories: {", ".join([f"{cat} (₹{amount:,.2f})" for cat, amount in top_categories])}"
            else:
                insights = "Add more transactions to discover detailed spending patterns."

            flash(f"Transaction added successfully! {insights}", "success")
        else:
            remaining = 5 - transaction_count
            flash(
                f"Transaction added successfully! Add {remaining} more transaction(s) to see spending patterns.",
                "success",
            )

    except Exception as e:
        print(f"Add transaction error: {str(e)}")
        db.session.rollback()
        flash("Error adding transaction. Please try again.", "error")

    return redirect(url_for("dashboard"))


@app.route("/analytics")
@login_required
def analytics():
    try:
        # Get user transactions
        transactions = Transaction.query.filter_by(user_id=current_user.id).all()

        # Initialize basic metrics with safe type conversion
        try:
            total_income = sum(float(t.amount) for t in transactions if t.transaction_type == "income")
            total_expenses = sum(float(t.amount) for t in transactions if t.transaction_type == "expense")
            remaining_amount = total_income - total_expenses
        except (ValueError, TypeError):
            flash("Error processing transaction amounts", "error")
            return redirect(url_for("dashboard"))

        # Initialize data structures
        monthly_data = {}
        monthly_savings = {}
        daily_expenses = {}
        category_data = {}
        category_trends = {}
        highest_category = {"category": "None", "amount": 0.0}

        # Process transactions for monthly analysis
        for transaction in transactions:
            try:
                month_key = transaction.date.strftime("%Y-%m")
                day_key = transaction.date.strftime("%A")
                amount = float(transaction.amount)

                # Initialize monthly data structure
                if month_key not in monthly_data:
                    monthly_data[month_key] = {
                        "income": 0.0,
                        "expenses": 0.0,
                        "net": 0.0,
                        "categories": {},
                    }

                # Initialize daily data structure
                if day_key not in daily_expenses:
                    daily_expenses[day_key] = 0.0

                # Update monthly data
                if transaction.transaction_type == "income":
                    monthly_data[month_key]["income"] += amount
                else:
                    monthly_data[month_key]["expenses"] += amount
                    daily_expenses[day_key] += amount

                    # Update category data
                    if transaction.category not in monthly_data[month_key]["categories"]:
                        monthly_data[month_key]["categories"][transaction.category] = 0.0
                    monthly_data[month_key]["categories"][transaction.category] += amount

                    # Update overall category data
                    if transaction.category not in category_data:
                        category_data[transaction.category] = 0.0
                        category_trends[transaction.category] = []
                    category_data[transaction.category] += amount
            except (ValueError, TypeError, AttributeError) as e:
                print(f"Error processing transaction {transaction.id}: {str(e)}")
                continue

        # Calculate monthly net and savings
        for month in monthly_data:
            try:
                monthly_data[month]["net"] = (
                    monthly_data[month]["income"] - monthly_data[month]["expenses"]
                )
                monthly_savings[month] = monthly_data[month]["net"]
            except Exception as e:
                print(f"Error calculating net for month {month}: {str(e)}")
                monthly_data[month]["net"] = 0.0
                monthly_savings[month] = 0.0

        # Calculate category trends
        sorted_months = sorted(monthly_data.keys())
        for category in category_trends:
            try:
                for month in sorted_months:
                    amount = sum(
                        float(t.amount)
                        for t in transactions
                        if t.transaction_type == "expense"
                        and t.category == category
                        and t.date.strftime("%Y-%m") == month
                    )
                    category_trends[category].append(float(amount))
            except Exception as e:
                print(f"Error calculating trend for category {category}: {str(e)}")
                category_trends[category] = [0.0] * len(sorted_months)

        # Calculate averages and ratios safely
        try:
            savings_rate = (
                (total_income - total_expenses) / total_income * 100
                if total_income > 0
                else 0.0
            )
            expense_ratio = (
                total_expenses / total_income * 100 if total_income > 0 else 0.0
            )
        except ZeroDivisionError:
            savings_rate = 0.0
            expense_ratio = 0.0

        # Calculate monthly averages safely
        try:
            if monthly_data:
                avg_monthly_income = sum(m["income"] for m in monthly_data.values()) / len(
                    monthly_data
                )
                avg_monthly_expenses = sum(
                    m["expenses"] for m in monthly_data.values()
                ) / len(monthly_data)
                avg_monthly_savings = sum(m["net"] for m in monthly_data.values()) / len(
                    monthly_data
                )

                # Simple moving average for forecasting
                last_three_months = (
                    list(monthly_data.values())[-3:]
                    if len(monthly_data) >= 3
                    else list(monthly_data.values())
                )
                expense_forecast = sum(m["expenses"] for m in last_three_months) / len(
                    last_three_months
                )
                income_forecast = sum(m["income"] for m in last_three_months) / len(
                    last_three_months
                )
            else:
                avg_monthly_income = avg_monthly_expenses = avg_monthly_savings = 0.0
                expense_forecast = income_forecast = 0.0
        except Exception as e:
            print(f"Error calculating monthly averages: {str(e)}")
            avg_monthly_income = avg_monthly_expenses = avg_monthly_savings = 0.0
            expense_forecast = income_forecast = 0.0

        # Find highest paid category safely
        try:
            if category_data:
                highest_cat = max(category_data.items(), key=lambda x: x[1])
                highest_category = {"category": highest_cat[0], "amount": float(highest_cat[1])}
        except Exception as e:
            print(f"Error finding highest category: {str(e)}")
            pass

        # Calculate AI Insights if enough data is available
        ai_insights = {"recommendations": [], "anomalies": [], "financial_health": None}
        if len(transactions) >= 5:
            try:
                df = pd.DataFrame(
                    [
                        {
                            "amount": float(t.amount),
                            "category": t.category,
                            "date": t.date,
                            "type": t.transaction_type,
                        }
                        for t in transactions
                    ]
                )

                # Basic financial health score
                recent_months = (
                    sorted(monthly_data.keys())[-3:]
                    if len(monthly_data) >= 3
                    else sorted(monthly_data.keys())
                )
                recent_data = [monthly_data[m] for m in recent_months]

                if recent_data:
                    try:
                        avg_savings_rate = np.mean(
                            [
                                d["net"] / d["income"] * 100 if d["income"] > 0 else 0
                                for d in recent_data
                            ]
                        )

                        expense_stability = 1 - (
                            np.std([d["expenses"] for d in recent_data])
                            /
                            np.mean([d["expenses"] for d in recent_data])
                            if np.mean([d["expenses"] for d in recent_data]) > 0
                            else 0
                        )

                        if avg_savings_rate > 20 and expense_stability > 0.7:
                            ai_insights["financial_health"] = "Excellent"
                            ai_insights["recommendations"].append(
                                "Keep up the great work! Your financial health is excellent."
                            )
                        elif avg_savings_rate > 10 and expense_stability > 0.5:
                            ai_insights["financial_health"] = "Good"
                            ai_insights["recommendations"].append(
                                "Your financial health is good. Consider increasing savings."
                            )
                        else:
                            ai_insights["financial_health"] = "Needs Improvement"
                            ai_insights["recommendations"].append(
                                "Focus on reducing expenses and increasing savings rate."
                            )
                    except Exception as e:
                        print(f"Error calculating financial health: {str(e)}")
                        ai_insights["financial_health"] = "Unknown"

                # Anomaly Detection (simple outlier detection for expenses)
                expense_transactions = df[df["type"] == "expense"]
                if not expense_transactions.empty:
                    amounts = expense_transactions["amount"].values.reshape(-1, 1)
                    if len(amounts) >= 2:
                        kmeans = KMeans(n_clusters=2, random_state=0, n_init=10).fit(amounts)
                        labels = kmeans.labels_
                        # Assume the cluster with smaller mean is normal, larger mean is potential anomaly
                        if kmeans.cluster_centers_[0] < kmeans.cluster_centers_[1]:
                            normal_cluster = 0
                            anomaly_cluster = 1
                        else:
                            normal_cluster = 1
                            anomaly_cluster = 0

                        anomalies = expense_transactions[labels == anomaly_cluster]
                        if not anomalies.empty:
                            for _, row in anomalies.iterrows():
                                ai_insights["anomalies"].append(
                                    f"Potential anomaly: Large expense of ₹{row["amount"]:,.2f} in {row["category"]} on {row["date"].strftime("%Y-%m-%d")}."
                                )

                # Spending Recommendations (based on top categories)
                if category_data:
                    sorted_categories = sorted(
                        category_data.items(), key=lambda item: item[1], reverse=True
                    )
                    top_spending_category = sorted_categories[0][0]
                    ai_insights["recommendations"].append(
                        f"Consider setting a budget for your top spending category: {top_spending_category}."
                    )

            except Exception as e:
                print(f"AI Insights calculation error: {str(e)}")
                ai_insights["recommendations"].append(
                    "Could not generate detailed AI insights due to data processing error."
                )

        return render_template(
            "analytics.html",
            total_income=total_income,
            total_expenses=total_expenses,
            remaining_amount=remaining_amount,
            monthly_data=monthly_data,
            monthly_savings=monthly_savings,
            daily_expenses=daily_expenses,
            category_data=category_data,
            category_trends=category_trends,
            highest_category=highest_category,
            savings_rate=savings_rate,
            expense_ratio=expense_ratio,
            avg_monthly_income=avg_monthly_income,
            avg_monthly_expenses=avg_monthly_expenses,
            avg_monthly_savings=avg_monthly_savings,
            expense_forecast=expense_forecast,
            income_forecast=income_forecast,
            ai_insights=ai_insights,
        )
    except Exception as e:
        print(f"Analytics error: {str(e)}")
        flash("An error occurred loading analytics.", "error")
        return redirect(url_for("dashboard"))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


if __name__ == "__main__":
    # Ensure the database is initialized before running the app
    with app.app_context():
        if not os.path.exists("instance/finance.db"):
            print("Database does not exist. Initializing...")
            db.create_all()
            print("Database initialized.")
        else:
            print("Database already exists.")
    app.run(debug=True)


