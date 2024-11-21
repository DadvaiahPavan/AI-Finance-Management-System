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
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///finance.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy()
db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# User Model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    transactions = db.relationship('Transaction', backref='user', lazy=True)

# Transaction Model
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # 'income' or 'expense'
    description = db.Column(db.String(200))
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('register'))
            
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, email=email, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.desc()).all()
    
    # Calculate financial summary
    total_income = sum(t.amount for t in transactions if t.transaction_type == 'income')
    total_expenses = sum(t.amount for t in transactions if t.transaction_type == 'expense')
    balance = total_income - total_expenses
    
    # Get monthly summary
    current_month = datetime.utcnow().month
    monthly_transactions = [t for t in transactions if t.date.month == current_month]
    monthly_income = sum(t.amount for t in monthly_transactions if t.transaction_type == 'income')
    monthly_expenses = sum(t.amount for t in monthly_transactions if t.transaction_type == 'expense')
    
    return render_template('dashboard.html', 
                         transactions=transactions,
                         total_income=total_income,
                         total_expenses=total_expenses,
                         balance=balance,
                         monthly_income=monthly_income,
                         monthly_expenses=monthly_expenses)

@app.route('/add_transaction', methods=['POST'])
@login_required
def add_transaction():
    amount = float(request.form.get('amount'))
    category = request.form.get('category')
    transaction_type = request.form.get('transaction_type')
    description = request.form.get('description')
    
    transaction = Transaction(
        amount=amount,
        category=category,
        transaction_type=transaction_type,
        description=description,
        user_id=current_user.id
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
            if t.transaction_type == 'expense':
                if t.category not in spending_data:
                    spending_data[t.category] = 0
                spending_data[t.category] += t.amount
        
        # Find top spending categories
        sorted_spending = sorted(spending_data.items(), key=lambda x: x[1], reverse=True)
        top_categories = sorted_spending[:3] if len(sorted_spending) >= 3 else sorted_spending
        
        # Generate spending insights
        if top_categories:
            insights = f"Top spending categories: {', '.join([f'{cat} (₹{amount:,.2f})' for cat, amount in top_categories])}"
        else:
            insights = "Add more transactions to discover detailed spending patterns."
        
        flash(f'Transaction added successfully! {insights}', 'success')
    else:
        remaining = 5 - transaction_count
        flash(f'Transaction added successfully! Add {remaining} more transaction(s) to see spending patterns.', 'success')
    
    return redirect(url_for('dashboard'))

@app.route('/analytics')
@login_required
def analytics():
    try:
        # Get user transactions
        transactions = Transaction.query.filter_by(user_id=current_user.id).all()
        
        # Initialize basic metrics with safe type conversion
        try:
            total_income = sum(float(t.amount) for t in transactions if t.transaction_type == 'income')
            total_expenses = sum(float(t.amount) for t in transactions if t.transaction_type == 'expense')
            remaining_amount = total_income - total_expenses
        except (ValueError, TypeError):
            flash('Error processing transaction amounts', 'error')
            return redirect(url_for('dashboard'))
        
        # Initialize data structures
        monthly_data = {}
        monthly_savings = {}
        daily_expenses = {}
        category_data = {}
        category_trends = {}
        highest_category = {'category': 'None', 'amount': 0.0}
        
        # Process transactions for monthly analysis
        for transaction in transactions:
            try:
                month_key = transaction.date.strftime('%Y-%m')
                day_key = transaction.date.strftime('%A')
                amount = float(transaction.amount)
                
                # Initialize monthly data structure
                if month_key not in monthly_data:
                    monthly_data[month_key] = {
                        'income': 0.0,
                        'expenses': 0.0,
                        'net': 0.0,
                        'categories': {}
                    }
                
                # Initialize daily data structure
                if day_key not in daily_expenses:
                    daily_expenses[day_key] = 0.0
                
                # Update monthly data
                if transaction.transaction_type == 'income':
                    monthly_data[month_key]['income'] += amount
                else:
                    monthly_data[month_key]['expenses'] += amount
                    daily_expenses[day_key] += amount
                    
                    # Update category data
                    if transaction.category not in monthly_data[month_key]['categories']:
                        monthly_data[month_key]['categories'][transaction.category] = 0.0
                    monthly_data[month_key]['categories'][transaction.category] += amount
                    
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
                monthly_data[month]['net'] = monthly_data[month]['income'] - monthly_data[month]['expenses']
                monthly_savings[month] = monthly_data[month]['net']
            except Exception as e:
                print(f"Error calculating net for month {month}: {str(e)}")
                monthly_data[month]['net'] = 0.0
                monthly_savings[month] = 0.0
        
        # Calculate category trends
        sorted_months = sorted(monthly_data.keys())
        for category in category_trends:
            try:
                for month in sorted_months:
                    amount = sum(float(t.amount) for t in transactions 
                               if t.transaction_type == 'expense' 
                               and t.category == category 
                               and t.date.strftime('%Y-%m') == month)
                    category_trends[category].append(float(amount))
            except Exception as e:
                print(f"Error calculating trend for category {category}: {str(e)}")
                category_trends[category] = [0.0] * len(sorted_months)
        
        # Calculate averages and ratios safely
        try:
            savings_rate = (total_income - total_expenses) / total_income * 100 if total_income > 0 else 0.0
            expense_ratio = total_expenses / total_income * 100 if total_income > 0 else 0.0
        except ZeroDivisionError:
            savings_rate = 0.0
            expense_ratio = 0.0
        
        # Calculate monthly averages safely
        try:
            if monthly_data:
                avg_monthly_income = sum(m['income'] for m in monthly_data.values()) / len(monthly_data)
                avg_monthly_expenses = sum(m['expenses'] for m in monthly_data.values()) / len(monthly_data)
                avg_monthly_savings = sum(m['net'] for m in monthly_data.values()) / len(monthly_data)
                
                # Simple moving average for forecasting
                last_three_months = list(monthly_data.values())[-3:]
                expense_forecast = sum(m['expenses'] for m in last_three_months) / len(last_three_months)
                income_forecast = sum(m['income'] for m in last_three_months) / len(last_three_months)
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
                highest_category = {
                    'category': highest_cat[0],
                    'amount': float(highest_cat[1])
                }
        except Exception as e:
            print(f"Error finding highest category: {str(e)}")
            pass
        
        # Calculate AI Insights if enough data is available
        ai_insights = {'recommendations': [], 'anomalies': [], 'financial_health': None}
        if len(transactions) >= 5:
            try:
                df = pd.DataFrame([{
                    'amount': float(t.amount),
                    'category': t.category,
                    'date': t.date,
                    'type': t.transaction_type
                } for t in transactions])
                
                # Basic financial health score
                recent_months = sorted(monthly_data.keys())[-3:] if len(monthly_data) >= 3 else sorted(monthly_data.keys())
                recent_data = [monthly_data[m] for m in recent_months]
                
                if recent_data:
                    try:
                        avg_savings_rate = np.mean([
                            d['net'] / d['income'] * 100 if d['income'] > 0 else 0 
                            for d in recent_data
                        ])
                        
                        expense_stability = 1 - (
                            np.std([d['expenses'] for d in recent_data]) / 
                            np.mean([d['expenses'] for d in recent_data])
                        ) if len(recent_data) > 1 else 0
                        
                        ai_insights['financial_health'] = {
                            'savings_rate': float(avg_savings_rate),
                            'expense_stability': float(expense_stability * 100),
                            'overall_score': float((avg_savings_rate + expense_stability * 100) / 2)
                        }
                    except Exception as e:
                        print(f"Error calculating financial health: {str(e)}")
                        pass
                
                # Anomaly detection
                if len(df) >= 5:
                    try:
                        expenses = df[df['type'] == 'expense']
                        mean_expense = expenses['amount'].mean()
                        std_expense = expenses['amount'].std()
                        threshold = 2
                        
                        anomalies = expenses[abs(expenses['amount'] - mean_expense) > threshold * std_expense]
                        ai_insights['anomalies'] = [{
                            'date': row['date'].strftime('%Y-%m-%d'),
                            'amount': float(row['amount']),
                            'category': row['category'],
                            'deviation': float(abs(row['amount'] - mean_expense) / std_expense)
                        } for _, row in anomalies.iterrows()]
                    except Exception as e:
                        print(f"Error in anomaly detection: {str(e)}")
                        pass
                
                # Generate recommendations
                try:
                    if ai_insights.get('financial_health', {}).get('savings_rate', 0) < 20:
                        ai_insights['recommendations'].append({
                            'type': 'savings',
                            'priority': 'high',
                            'message': 'Consider increasing your savings rate to at least 20% of your income.',
                            'impact': 'high'
                        })
                    
                    if category_data:
                        high_spending_categories = sorted(
                            [(cat, amt / total_expenses * 100) for cat, amt in category_data.items()],
                            key=lambda x: x[1],
                            reverse=True
                        )[:3]
                        
                        for category, percentage in high_spending_categories:
                            if percentage > 30:
                                ai_insights['recommendations'].append({
                                    'type': 'category',
                                    'priority': 'medium',
                                    'message': f'Your spending in {category} is {percentage:.1f}% of total expenses. Consider setting a budget for this category.',
                                    'impact': 'medium'
                                })
                except Exception as e:
                    print(f"Error generating recommendations: {str(e)}")
                    pass
            
            except Exception as e:
                print(f"Error in AI insights calculation: {str(e)}")
                pass
        
        return render_template(
            "analytics.html",
            monthly_data=monthly_data,
            monthly_savings=monthly_savings,
            category_data=category_data,
            category_trends=category_trends,
            daily_expenses=daily_expenses,
            total_income=float(total_income),
            total_expenses=float(total_expenses),
            remaining_amount=float(remaining_amount),
            avg_monthly_income=float(avg_monthly_income),
            avg_monthly_expenses=float(avg_monthly_expenses),
            avg_monthly_savings=float(avg_monthly_savings),
            savings_rate=float(savings_rate),
            expense_ratio=float(expense_ratio),
            expense_forecast=float(expense_forecast),
            income_forecast=float(income_forecast),
            highest_category=highest_category,
            ai_insights=ai_insights
        )
        
    except Exception as e:
        print(f"Error in analytics route: {str(e)}")
        flash('An error occurred while generating analytics', 'error')
        return redirect(url_for('dashboard'))

@app.route('/ai_insights')
@login_required
def ai_insights():
    try:
        transactions = Transaction.query.filter_by(user_id=current_user.id).all()
        if len(transactions) < 3:  # Reduced minimum requirement
            return render_template('ai_insights.html', error='Not enough transaction data. Need at least 3 transactions.')

        # Convert transactions to DataFrame
        df = pd.DataFrame([{
            'amount': float(t.amount),
            'category': t.category,
            'date': t.date,
            'type': t.transaction_type,
            'description': t.description
        } for t in transactions])

        # Calculate basic metrics
        expense_df = df[df['type'] == 'expense']
        income_df = df[df['type'] == 'income']
        
        total_income = income_df['amount'].sum()
        total_expenses = expense_df['amount'].sum()
        savings_rate = ((total_income - total_expenses) / total_income * 100) if total_income > 0 else 0

        # Category analysis
        category_spending = expense_df.groupby('category')['amount'].agg(['sum', 'mean', 'count']).round(2)
        category_spending['percentage'] = (category_spending['sum'] / total_expenses * 100).round(2)
        
        # Spending patterns analysis
        spending_patterns = analyze_spending_patterns(expense_df)
        
        # Risk analysis
        risk_analysis = analyze_risk(df)
        
        # Generate recommendations
        recommendations = generate_recommendations(category_spending, risk_analysis, savings_rate)

        # Prepare template data
        template_data = {
            'financial_health': {
                'total_income': float(total_income),
                'total_expenses': float(total_expenses),
                'savings_rate': float(savings_rate),
                'risk_level': risk_analysis['overall_risk'],
                'expense_volatility': risk_analysis['scores']['expense_volatility'],
                'income_stability': risk_analysis['scores']['income_stability']
            },
            'spending_analysis': {
                'categories': category_spending.to_dict('index'),
                'patterns': spending_patterns,
                'top_expenses': category_spending.nlargest(3, 'percentage').index.tolist()
            },
            'recommendations': recommendations,
            'time_series_data': prepare_time_series_data(df),
            'risk_analysis': risk_analysis
        }

        return render_template(
            'ai_insights.html',
            data=template_data,
            error=None
        )

    except Exception as e:
        print(f"Error in AI insights: {str(e)}")
        return render_template('ai_insights.html', error=str(e))

def analyze_spending_patterns(expense_df):
    try:
        category_pivot = pd.pivot_table(
            expense_df,
            values='amount',
            index='date',
            columns='category',
            fill_value=0
        )

        if len(category_pivot) >= 2:
            scaler = StandardScaler()
            normalized_data = scaler.fit_transform(category_pivot)
            
            max_clusters = min(3, len(category_pivot) // 2)
            if max_clusters >= 2:
                kmeans = KMeans(n_clusters=max_clusters, random_state=42)
                clusters = kmeans.fit_predict(normalized_data)
                
                cluster_insights = []
                for i in range(max_clusters):
                    cluster_data = category_pivot.iloc[clusters == i]
                    avg_spending = {
                        cat: float(cluster_data[cat].mean())
                        for cat in category_pivot.columns
                    }
                    
                    cluster_insights.append({
                        'size': int(sum(clusters == i)),
                        'avg_spending': avg_spending,
                        'dominant_categories': [
                            cat for cat, val in sorted(
                                avg_spending.items(),
                                key=lambda x: x[1],
                                reverse=True
                            )[:3]
                        ],
                        'description': generate_cluster_description(avg_spending)
                    })
                
                return {
                    'clusters': cluster_insights,
                    'total_patterns': len(cluster_insights)
                }
    except Exception as e:
        print(f"Error in spending pattern analysis: {str(e)}")
    
    return {'clusters': [], 'total_patterns': 0}

def analyze_risk(df):
    risk_analysis = {
        'scores': {
            'expense_volatility': 0,
            'income_stability': 0,
            'savings_rate': 0,
            'emergency_fund': 0,
            'debt_to_income': 0,
            'expense_to_income': 0
        },
        'overall_risk': 'Low',
        'details': [],
        'indicators': {}
    }

    try:
        # Monthly aggregations
        monthly_expenses = df[df['type'] == 'expense'].groupby(
            df['date'].dt.strftime('%Y-%m')
        )['amount'].sum()

        monthly_income = df[df['type'] == 'income'].groupby(
            df['date'].dt.strftime('%Y-%m')
        )['amount'].sum()

        # Calculate risk metrics
        if len(monthly_expenses) >= 2:
            expense_volatility = float(monthly_expenses.std() / monthly_expenses.mean())
            risk_analysis['scores']['expense_volatility'] = min(100, expense_volatility * 100)
            risk_analysis['indicators']['expense_volatility'] = {
                'status': 'High' if expense_volatility > 0.5 else 'Medium' if expense_volatility > 0.3 else 'Low',
                'value': f"{expense_volatility:.2f}",
                'description': 'Measures how much your expenses fluctuate month to month'
            }
            
            if expense_volatility > 0.5:
                risk_analysis['details'].append({
                    'type': 'warning',
                    'message': 'High expense volatility detected. Consider more consistent spending patterns.',
                    'score_impact': -20
                })

        if len(monthly_income) >= 2:
            income_stability = float(1 - (monthly_income.std() / monthly_income.mean()))
            risk_analysis['scores']['income_stability'] = max(0, min(100, income_stability * 100))
            risk_analysis['indicators']['income_stability'] = {
                'status': 'Low' if income_stability < 0.5 else 'Medium' if income_stability < 0.7 else 'High',
                'value': f"{income_stability:.2f}",
                'description': 'Measures how consistent your income is month to month'
            }
            
            if income_stability < 0.5:
                risk_analysis['details'].append({
                    'type': 'warning',
                    'message': 'Income stability is low. Consider diversifying income sources.',
                    'score_impact': -25
                })

        # Calculate savings rate and emergency fund
        if not monthly_income.empty and not monthly_expenses.empty:
            avg_monthly_income = monthly_income.mean()
            avg_monthly_expense = monthly_expenses.mean()
            if avg_monthly_income > 0:
                savings_rate = ((avg_monthly_income - avg_monthly_expense) / avg_monthly_income) * 100
                risk_analysis['scores']['savings_rate'] = float(max(0, min(100, savings_rate)))
                
                # Emergency fund score (assuming 6 months of expenses is ideal)
                total_savings = max(0, sum(monthly_income) - sum(monthly_expenses))
                months_of_expenses = total_savings / avg_monthly_expense if avg_monthly_expense > 0 else 0
                emergency_fund_score = min(100, (months_of_expenses / 6) * 100)
                risk_analysis['scores']['emergency_fund'] = float(emergency_fund_score)
                
                risk_analysis['indicators']['savings_rate'] = {
                    'status': 'Low' if savings_rate < 20 else 'Medium' if savings_rate < 30 else 'High',
                    'value': f"{savings_rate:.1f}%",
                    'description': 'Percentage of income saved each month'
                }
                
                risk_analysis['indicators']['emergency_fund'] = {
                    'status': 'Low' if months_of_expenses < 3 else 'Medium' if months_of_expenses < 6 else 'High',
                    'value': f"{months_of_expenses:.1f} months",
                    'description': 'Number of months your savings could cover expenses'
                }
                
                if savings_rate < 20:
                    risk_analysis['details'].append({
                        'type': 'alert',
                        'message': 'Savings rate is below recommended 20%. Consider reducing non-essential expenses.',
                        'score_impact': -15
                    })
                
                if months_of_expenses < 3:
                    risk_analysis['details'].append({
                        'type': 'alert',
                        'message': 'Emergency fund is below 3 months of expenses. Focus on building your safety net.',
                        'score_impact': -20
                    })

        # Expense to Income Ratio
        if avg_monthly_income > 0:
            expense_ratio = (avg_monthly_expense / avg_monthly_income) * 100
            risk_analysis['scores']['expense_to_income'] = float(max(0, 100 - expense_ratio))
            risk_analysis['indicators']['expense_ratio'] = {
                'status': 'High' if expense_ratio > 90 else 'Medium' if expense_ratio > 70 else 'Low',
                'value': f"{expense_ratio:.1f}%",
                'description': 'Percentage of income spent on expenses'
            }
            
            if expense_ratio > 90:
                risk_analysis['details'].append({
                    'type': 'alert',
                    'message': 'Your expenses are consuming over 90% of your income. This is a high-risk situation.',
                    'score_impact': -30
                })

        # Overall risk assessment with weighted scores
        weights = {
            'expense_volatility': 0.2,
            'income_stability': 0.25,
            'savings_rate': 0.2,
            'emergency_fund': 0.2,
            'expense_to_income': 0.15
        }
        
        weighted_score = sum(
            risk_analysis['scores'][metric] * weight 
            for metric, weight in weights.items()
        )
        
        risk_analysis['overall_risk'] = (
            'High' if weighted_score < 40 else 
            'Medium' if weighted_score < 70 else 
            'Low'
        )
        risk_analysis['risk_score'] = float(weighted_score)

    except Exception as e:
        print(f"Error in risk analysis: {str(e)}")

    return risk_analysis

def generate_recommendations(category_spending, risk_analysis, savings_rate):
    recommendations = []
    
    # Risk-based recommendations
    if risk_analysis['overall_risk'] != 'Low':
        recommendations.append({
            'type': 'risk',
            'priority': 'high',
            'message': f"Your financial risk level is {risk_analysis['overall_risk']}. Build an emergency fund of at least 3-6 months of expenses.",
            'category': 'risk',
            'action_items': [
                'Set up automatic savings transfers',
                'Review and cut non-essential expenses',
                'Look for additional income opportunities'
            ]
        })
    
    # Emergency Fund recommendations
    if risk_analysis['scores']['emergency_fund'] < 50:
        recommendations.append({
            'type': 'emergency_fund',
            'priority': 'high',
            'message': 'Your emergency fund needs attention. Aim to save enough to cover 6 months of expenses.',
            'category': 'savings',
            'action_items': [
                'Set a monthly savings goal',
                'Create a separate emergency fund account',
                'Reduce discretionary spending'
            ]
        })
    
    # Income Stability recommendations
    if risk_analysis['scores']['income_stability'] < 70:
        recommendations.append({
            'type': 'income',
            'priority': 'high',
            'message': 'Your income shows significant fluctuations. Consider ways to stabilize your income.',
            'category': 'income',
            'action_items': [
                'Explore additional income sources',
                'Look for long-term employment opportunities',
                'Build skills for better job security'
            ]
        })
    
    # Savings recommendations
    if savings_rate < 20:
        recommendations.append({
            'type': 'savings',
            'priority': 'high',
            'message': 'Your savings rate is below the recommended 20%. Here are ways to increase your savings:',
            'category': 'savings',
            'action_items': [
                'Create a detailed budget',
                'Use the 50/30/20 budgeting rule',
                'Track all expenses for a month',
                'Cancel unused subscriptions'
            ]
        })
    
    # Expense Volatility recommendations
    if risk_analysis['scores']['expense_volatility'] > 60:
        recommendations.append({
            'type': 'expenses',
            'priority': 'medium',
            'message': 'Your expenses vary significantly month to month. Consider these steps for more consistent spending:',
            'category': 'expenses',
            'action_items': [
                'Create a monthly spending plan',
                'Identify and reduce variable expenses',
                'Set up bill payment reminders',
                'Build a buffer in your budget'
            ]
        })
    
    # Category-specific recommendations
    for category, row in category_spending.iterrows():
        if row['percentage'] > 30:
            recommendations.append({
                'type': 'budget',
                'priority': 'high' if row['percentage'] > 50 else 'medium',
                'message': f"Your {category} expenses are {row['percentage']:.1f}% of total expenses. Consider these reduction strategies:",
                'category': 'budget',
                'details': {
                    'category': category,
                    'current_spending': float(row['sum']),
                    'percentage': float(row['percentage'])
                },
                'action_items': [
                    f"Review all {category} expenses for potential savings",
                    f"Research cheaper alternatives for {category}",
                    f"Set a specific budget for {category}",
                    "Track spending in this category weekly"
                ]
            })
    
    # Debt recommendations if present
    if 'debt' in category_spending.index:
        debt_percentage = category_spending.loc['debt']['percentage']
        if debt_percentage > 20:
            recommendations.append({
                'type': 'debt',
                'priority': 'high',
                'message': 'Your debt payments are significant. Consider debt reduction strategies:',
                'category': 'debt',
                'action_items': [
                    'List all debts with interest rates',
                    'Consider debt consolidation',
                    'Use the debt avalanche method',
                    'Negotiate with creditors for better rates'
                ]
            })
    
    return recommendations

def prepare_time_series_data(df):
    try:
        expense_df = df[df['type'] == 'expense'].copy()
        expense_df['date'] = pd.to_datetime(expense_df['date'])
        
        # Daily aggregation
        daily_expenses = expense_df.groupby('date')['amount'].sum()
        
        # Calculate 7-day moving average
        ma7 = daily_expenses.rolling(window=7, min_periods=1).mean()
        
        # Prepare forecast (simple moving average projection)
        last_value = ma7.iloc[-1] if not ma7.empty else 0
        forecast_dates = pd.date_range(
            start=daily_expenses.index[-1] + pd.Timedelta(days=1),
            periods=7
        )
        
        return {
            'dates': daily_expenses.index.strftime('%Y-%m-%d').tolist(),
            'values': daily_expenses.round(2).tolist(),
            'ma7': ma7.round(2).tolist(),
            'forecast_dates': forecast_dates.strftime('%Y-%m-%d').tolist(),
            'forecast_values': [float(last_value)] * 7
        }
    except Exception as e:
        print(f"Error preparing time series data: {str(e)}")
        return {}

def generate_cluster_description(avg_spending):
    # Sort categories by spending amount
    sorted_cats = sorted(
        avg_spending.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    # Get top categories
    top_cats = [cat for cat, val in sorted_cats if val > 0][:3]
    
    if not top_cats:
        return "No significant spending pattern"
    
    return f"Primarily {', '.join(top_cats[:-1])} and {top_cats[-1]} expenses" if len(top_cats) > 1 else f"Mainly {top_cats[0]} expenses"

@app.route('/investments')
@login_required
def investments():
    try:
        print("Starting to fetch investment data...")
        
        # RapidAPI configuration
        headers = {
            'x-rapidapi-key': 'cd4e31604emsh7ed111fe92eb991p144247jsn974f92dca7e8',
            'x-rapidapi-host': 'yahoo-finance15.p.rapidapi.com'
        }
        
        # Get USD to INR conversion rate
        try:
            usd_inr_url = "https://yahoo-finance15.p.rapidapi.com/api/yahoo/qu/quote/INR=X"
            usd_inr_response = requests.get(usd_inr_url, headers=headers)
            if usd_inr_response.status_code == 200:
                usd_inr_data = usd_inr_response.json()
                if 'body' in usd_inr_data and usd_inr_data['body']:
                    usd_inr_rate = float(usd_inr_data['body'][0].get('regularMarketPrice', 83.0))  # Default to 83 if not available
                else:
                    usd_inr_rate = 83.0  # Default USD to INR rate
            else:
                usd_inr_rate = 83.0
        except Exception as e:
            print(f"Error fetching USD/INR rate: {str(e)}")
            usd_inr_rate = 83.0

        # Function to generate stock recommendations
        def generate_stock_recommendation(stock_data):
            if not stock_data:
                return "No stock data available for analysis."
            
            recommendations = []
            total_market_cap = sum(stock['market_cap'] for stock in stock_data if stock['market_cap'] > 0)
            
            for stock in stock_data:
                if stock['price'] == 0:
                    continue
                
                market_cap_ratio = stock['market_cap'] / total_market_cap if total_market_cap > 0 else 0
                change_percent = stock['change_percent']
                
                # Generate recommendation based on market cap and performance
                if change_percent <= -2:
                    if market_cap_ratio > 0.15:  # Large cap stock
                        recommendations.append(f"Consider buying {stock['name']} as it's a major company showing a significant dip of {abs(change_percent):.1f}%")
                elif change_percent >= 2:
                    if market_cap_ratio < 0.1:  # Small/Mid cap stock
                        recommendations.append(f"Consider booking partial profits in {stock['name']} as it's up by {change_percent:.1f}%")
                
                # Volume-based recommendations (if available)
                if 'volume' in stock and stock['volume'] > 0:
                    avg_volume = stock.get('averageDailyVolume3Month', stock['volume'])
                    if stock['volume'] > avg_volume * 1.5:
                        recommendations.append(f"Unusual high trading volume in {stock['name']}. Watch closely.")
            
            if not recommendations:
                recommendations.append("Market conditions are stable. Hold your current positions.")
            
            return recommendations

        # Popular Indian stocks to track (using NSE symbols)
        stocks = [
            {'id': 'RELIANCE.NS', 'name': 'Reliance Industries'},
            {'id': 'TCS.NS', 'name': 'Tata Consultancy Services'},
            {'id': 'HDFCBANK.NS', 'name': 'HDFC Bank'},
            {'id': 'INFY.NS', 'name': 'Infosys'},
            {'id': 'HINDUNILVR.NS', 'name': 'Hindustan Unilever'},
            {'id': 'ICICIBANK.NS', 'name': 'ICICI Bank'},
            {'id': 'SBIN.NS', 'name': 'State Bank of India'},
            {'id': 'BHARTIARTL.NS', 'name': 'Bharti Airtel'}
        ]
        stock_data = []
        
        print("Starting to fetch stock data...")
        
        # Get stock data
        for stock in stocks:
            try:
                print(f"\nFetching data for {stock['id']}...")
                
                # Get real-time quote using Yahoo Finance API
                url = f"https://yahoo-finance15.p.rapidapi.com/api/yahoo/qu/quote/{stock['id']}"
                
                response = requests.get(url, headers=headers)
                print(f"HTTP Response for {stock['id']}:", response.status_code)
                print(f"Response headers:", response.headers)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"Raw data for {stock['id']}:", data)
                        
                        if 'body' in data and isinstance(data['body'], list) and len(data['body']) > 0:
                            quote = data['body'][0]
                            
                            # Extract price and calculate changes
                            current_price = float(quote.get('regularMarketPrice', 0))
                            prev_close = float(quote.get('regularMarketPreviousClose', 0))
                            change = current_price - prev_close
                            change_percent = (change / prev_close * 100) if prev_close else 0
                            
                            stock_entry = {
                                'symbol': stock['id'].replace('.NS', ''),
                                'name': stock['name'],
                                'price': round(current_price, 2),  # Already in INR for Indian stocks
                                'change': round(change, 2),
                                'change_percent': round(change_percent, 2),
                                'high': round(float(quote.get('regularMarketDayHigh', 0)), 2),
                                'low': round(float(quote.get('regularMarketDayLow', 0)), 2),
                                'logo': '',
                                'market_cap': round(float(quote.get('marketCap', 0)) / 10000000, 2),  # Convert to Crores
                                'volume': float(quote.get('regularMarketVolume', 0)),
                                'averageDailyVolume3Month': float(quote.get('averageDailyVolume3Month', 0))
                            }
                            print(f"Processed stock entry for {stock['id']}:", stock_entry)
                            stock_data.append(stock_entry)
                        else:
                            print(f"Invalid data format for {stock['id']}")
                            raise Exception("Invalid data format")
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error for {stock['id']}: {str(e)}")
                        print("Response content:", response.text[:200])  # Print first 200 chars of response
                        raise Exception("Invalid JSON response")
                else:
                    print(f"Error response for {stock['id']}:", response.text)
                    raise Exception(f"HTTP request failed with status {response.status_code}")
                
                # Add delay to avoid rate limiting
                time.sleep(1)
                
            except Exception as e:
                print(f"Error processing {stock['id']}: {str(e)}")
                stock_data.append({
                    'symbol': stock['id'].replace('.NS', ''),
                    'name': stock['name'],
                    'price': 0,
                    'change': 0,
                    'change_percent': 0,
                    'high': 0,
                    'low': 0,
                    'logo': '',
                    'market_cap': 0
                })
        
        # For crypto data, we'll use a different endpoint
        crypto_data = []
        
        # Get crypto data
        crypto_symbols = [
            ('BTC-USD', 'Bitcoin (BTC)'),
            ('ETH-USD', 'Ethereum (ETH)')
        ]
        
        for symbol, name in crypto_symbols:
            try:
                print(f"\nFetching data for {symbol}...")
                
                url = f"https://yahoo-finance15.p.rapidapi.com/api/yahoo/qu/quote/{symbol}"
                
                response = requests.get(url, headers=headers)
                print(f"HTTP Response for {symbol}:", response.status_code)
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"Raw crypto data for {symbol}:", data)
                    
                    if 'body' in data and isinstance(data['body'], list) and len(data['body']) > 0:
                        quote = data['body'][0]
                        
                        crypto_entry = {
                            'symbol': name,
                            'price': round(float(quote.get('regularMarketPrice', 0)) * usd_inr_rate, 2),
                            'change': round(float(quote.get('regularMarketChange', 0)) * usd_inr_rate, 2),
                            'change_percent': round(float(quote.get('regularMarketChangePercent', 0)), 2),
                            'high': round(float(quote.get('regularMarketDayHigh', 0)) * usd_inr_rate, 2),
                            'low': round(float(quote.get('regularMarketDayLow', 0)) * usd_inr_rate, 2),
                            'volume': round(float(quote.get('regularMarketVolume', 0)), 2)
                        }
                        print(f"Processed crypto entry for {symbol}:", crypto_entry)
                        crypto_data.append(crypto_entry)
                    else:
                        print(f"Invalid data format for crypto {symbol}")
                        raise Exception("Invalid data format")
                else:
                    raise Exception(f"HTTP request failed with status {response.status_code}")
                
                time.sleep(1)
                
            except Exception as e:
                print(f"Error processing crypto {symbol}: {str(e)}")
                crypto_data.append({
                    'symbol': name,
                    'price': 0,
                    'change': 0,
                    'change_percent': 0,
                    'high': 0,
                    'low': 0,
                    'volume': 0
                })
        
        print("\nFinal data:")
        print("Stock data:", stock_data)
        print("Crypto data:", crypto_data)
        
        # Generate recommendations
        stock_recommendations = generate_stock_recommendation(stock_data)
        
        # Generate crypto recommendations
        crypto_recommendations = []
        for crypto in crypto_data:
            if crypto['change_percent'] <= -5:
                crypto_recommendations.append(f"Consider averaging down on {crypto['symbol']} as it's down {abs(crypto['change_percent']):.1f}%")
            elif crypto['change_percent'] >= 5:
                crypto_recommendations.append(f"Consider taking partial profits on {crypto['symbol']} as it's up {crypto['change_percent']:.1f}%")
        
        if not crypto_recommendations:
            crypto_recommendations.append("Crypto market is showing normal volatility. Maintain your current strategy.")

        return render_template('investments.html', 
                             stock_data=stock_data, 
                             crypto_data=crypto_data,
                             stock_recommendations=stock_recommendations,
                             crypto_recommendations=crypto_recommendations)
        
    except Exception as e:
        print(f"Major error in investments route: {str(e)}")
        return render_template(
            'investments.html',
            stock_data=[],
            crypto_data=[],
            error="Failed to fetch investment data. Please try again later."
        )

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
      with app.app_context():
        db.create_all()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
