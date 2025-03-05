from django.shortcuts import render, redirect, get_object_or_404
from .models import Expense, Category
from .forms import ExpenseForm, CategoryForm
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib import messages
from allauth.account.views import SignupView
from django.core.mail import send_mail
from smtplib import SMTPException

@login_required
def expenses_list(request):
    expenses = Expense.objects.filter(user=request.user).order_by('-date')
    return render(request, 'expenses_list.html', {'expenses': expenses})

@login_required
def add_expense(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user
            
            # Convert date to datetime
            date = form.cleaned_data.get('date')
            if date:
                # Combine date with current time
                current_time = timezone.now().time()
                datetime_obj = datetime.combine(date, current_time)
                # Make it timezone aware
                expense.date = timezone.make_aware(datetime_obj)
            
            # Handle custom category
            custom_category = form.cleaned_data.get('custom_category')
            if custom_category:
                category, created = Category.objects.get_or_create(
                    name=custom_category,
                    defaults={'user': request.user}
                )
                expense.category = category
            
            # Handle custom payment method
            if expense.payment_method == 'custom':
                expense.payment_method = form.cleaned_data.get('custom_payment_method')
            
            # Save receipt image
            if 'receipt_image' in request.FILES:
                expense.receipt_image = request.FILES['receipt_image']
            
            expense.save()
            return redirect('expenses_list')
    else:
        form = ExpenseForm()
    return render(request, 'add_expense.html', {'form': form})

@login_required
def monthly_report(request):
    # Get current month's expenses
    today = timezone.now().date()
    first_day = today.replace(day=1)
    
    expenses = Expense.objects.filter(
        user=request.user,
        date__date__gte=first_day,
        date__date__lte=today
    )
    
    # Calculate total expenses
    total = expenses.aggregate(total=Sum('amount'))['total'] or 0
    
    # Get highest expense
    highest_expense = expenses.order_by('-amount').first()
    highest_amount = highest_expense.amount if highest_expense else 0
    
    # Get most active day (day with most expenses)
    expenses_by_day = expenses.values('date__date').annotate(
        count=Count('id'),
        total=Sum('amount')
    ).order_by('-count').first()
    
    most_active_day = expenses_by_day['date__date'].strftime('%B %d') if expenses_by_day else 'No data'
    
    # Get expenses by category for the chart
    category_expenses = Category.objects.filter(
        expense__user=request.user,
        expense__date__date__gte=first_day,
        expense__date__date__lte=today
    ).annotate(
        total=Sum('expense__amount')
    ).values('name', 'total')
    
    context = {
        'expenses': expenses,
        'total': total,
        'highest_expense': highest_amount,
        'most_active_day': most_active_day,
        'category_expenses': category_expenses,
    }
    return render(request, 'monthly_report.html', context)

@login_required
def home(request):
    # Get today's expenses
    today = timezone.now().date()
    today_expenses = Expense.objects.filter(
        user=request.user,
        date__date=today
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Get this month's expenses
    first_day = today.replace(day=1)
    monthly_expenses = Expense.objects.filter(
        user=request.user,
        date__date__gte=first_day,
        date__date__lte=today
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Get expenses by category
    categories = Category.objects.filter(
        expense__user=request.user
    ).annotate(total=Sum('expense__amount'))

    # Recent expenses
    recent_expenses = Expense.objects.filter(
        user=request.user
    ).order_by('-date')[:5]

    context = {
        'today_expenses': today_expenses,
        'monthly_expenses': monthly_expenses,
        'categories': categories,
        'recent_expenses': recent_expenses,
    }
    return render(request, 'home.html', context)

@login_required
def edit_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id, user=request.user)
    
    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES, instance=expense)
        if form.is_valid():
            expense = form.save(commit=False)
            
            # Convert date to datetime
            date = form.cleaned_data.get('date')
            if date:
                current_time = timezone.now().time()
                datetime_obj = datetime.combine(date, current_time)
                expense.date = timezone.make_aware(datetime_obj)
            
            # Handle custom payment method
            if expense.payment_method == 'custom':
                expense.payment_method = form.cleaned_data.get('custom_payment_method')
            
            # Handle receipt image
            if 'receipt_image' in request.FILES:
                expense.receipt_image = request.FILES['receipt_image']
            
            expense.save()
            messages.success(request, 'Expense updated successfully!')
            return redirect('expenses_list')
    else:
        form = ExpenseForm(instance=expense)
    
    return render(request, 'edit_expense.html', {'form': form, 'expense': expense})

@login_required
def delete_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id, user=request.user)
    
    if request.method == 'POST':
        expense.delete()
        messages.success(request, 'Expense deleted successfully!')
        return redirect('expenses_list')
    
    return render(request, 'delete_expense.html', {'expense': expense})

class CustomSignupView(SignupView):
    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except (ConnectionRefusedError, SMTPException):
            return render(self.request, 'account/email_verification_error.html')