from flask import Flask, request, jsonify
from flask_restful import Resource, Api
from datetime import datetime
from models import db, Expense, ExpenseCategory
from config import Config
from decimal import Decimal, InvalidOperation

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
api = Api(app)

class ExpenseResource(Resource):

    def get(self, id):
        expense = Expense.query.get_or_404(id)
        expense_data = {
            'id': expense.id,
            'user_id': expense.user_id,
            'amount': str(expense.amount),
            'category_id': expense.category_id,
            'date': expense.date.strftime('%Y-%m-%d'),
            'description': expense.description,
            'is_recurring': expense.is_recurring,
            'created_at': expense.created_at.isoformat(),
            'updated_at': expense.updated_at.isoformat()
        }
        return jsonify({'expense': expense_data})

    def delete(self, id):
        expense = Expense.query.get_or_404(id)
        category = ExpenseCategory.query.get_or_404(expense.category_id)
        
        total_expenses = sum(Decimal(e.amount) for e in Expense.query.filter_by(category_id=category.id).all() if e.id != id)
        
        if category.limit and total_expenses > Decimal(category.limit):
            return jsonify({'message': 'Cannot delete expense: category limit would be exceeded'}), 400
        
        db.session.delete(expense)
        db.session.commit()

        return jsonify({'message': 'Expense deleted successfully'})
    
    def post(self):
        data = request.get_json()
        user_id = data.get('user_id')
        amount = Decimal(data.get('amount'))
        category_id = data.get('category_id')
        date = datetime.strptime(data.get('date'), '%Y-%m-%d')
        description = data.get('description')

        category = ExpenseCategory.query.get_or_404(category_id)

        total_expenses = sum(Decimal(expense.amount) for expense in Expense.query.filter_by(category_id=category_id).all()) + amount
        
        if category.limit and total_expenses > Decimal(category.limit):
            return jsonify({'message': 'Cannot add expense: category limit exceeded'}), 400

        new_expense = Expense(
            user_id=user_id, 
            amount=amount, 
            category_id=category_id, 
            date=date, 
            description=description
        )
        db.session.add(new_expense)
        db.session.commit()

        return jsonify({'message': 'Expense created successfully'}), 201

    def put(self, id):
        data = request.get_json()
        expense = Expense.query.get_or_404(id)
        category = ExpenseCategory.query.get_or_404(expense.category_id)

        new_amount = Decimal(data.get('amount', expense.amount))
        
        total_expenses = sum(Decimal(e.amount) for e in Expense.query.filter_by(category_id=category.id).all() if e.id != id) + new_amount
        
        if category.limit and total_expenses > Decimal(category.limit):
            return jsonify({'message': 'Cannot update expense: category limit exceeded'}), 400

        expense.user_id = data.get('user_id', expense.user_id)
        expense.amount = new_amount
        expense.category_id = data.get('category_id', expense.category_id)
        expense.date = datetime.strptime(data.get('date', expense.date.strftime('%Y-%m-%d')), '%Y-%m-%d')
        expense.description = data.get('description', expense.description)

        db.session.commit()

        return jsonify({'message': 'Expense updated successfully'})


class ExpenseCategoryResource(Resource):
    def get(self, id=None):
        if id:
            category = ExpenseCategory.query.get_or_404(id)
            category_data = {
                'id': category.id,
                'name': category.name,
                'description': category.description,
                'user_id': category.user_id,
                'limit': str(category.limit)  # Convert limit to string for JSON serialization
            }
            return jsonify({'category': category_data})
        else:
            categories = ExpenseCategory.query.all()
            output = []
            for category in categories:
                category_data = {
                    'id': category.id,
                    'name': category.name,
                    'description': category.description,
                    'user_id': category.user_id,
                    'limit': str(category.limit)  # Convert limit to string for JSON serialization
                }
                output.append(category_data)
            return jsonify({'categories': output})

    def post(self):
        data = request.get_json()
        name = data.get('name')
        description = data.get('description')
        user_id = data.get('user_id')
        limit_str = data.get('limit')  # Optional limit field

        try:
            limit = Decimal(limit_str) if limit_str else None
        except (InvalidOperation, ValueError):
            return jsonify({'message': 'Invalid limit value'}), 400

        # Create new category
        new_category = ExpenseCategory(
            name=name, 
            description=description, 
            user_id=user_id, 
            limit=limit
        )
        db.session.add(new_category)
        db.session.commit()

        return jsonify({'message': 'Category created successfully'}), 201

    def put(self, id):
        data = request.get_json()
        category = ExpenseCategory.query.get_or_404(id)

        category.name = data.get('name', category.name)
        category.description = data.get('description', category.description)
        category.user_id = data.get('user_id', category.user_id)
        
        limit_str = data.get('limit')
        if limit_str is not None:
            try:
                category.limit = Decimal(limit_str)
            except (InvalidOperation, ValueError):
                return jsonify({'message': 'Invalid limit value'}), 400

        db.session.commit()

        return jsonify({'message': 'Category updated successfully'})

    def delete(self, id):
        category = ExpenseCategory.query.get_or_404(id)
        db.session.delete(category)
        db.session.commit()

        return jsonify({'message': 'Category deleted successfully'})

if __name__ == '__main__':
    app.run(debug=True)
