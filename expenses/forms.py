from django import forms
from .models import Expense, Category
from django.utils import timezone

class ExpenseForm(forms.ModelForm):
    amount = forms.DecimalField(
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': '₹ 0.00',
            'step': '0.01',
            'min': '0'
        })
    )
    
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-input',
            'placeholder': 'What did you spend on?',
            'rows': '3'
        })
    )
    
    date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-input'
        }),
        initial=timezone.now
    )
    
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        widget=forms.Select(attrs={
            'class': 'form-select category-select'
        })
    )

    class Meta:
        model = Expense
        fields = ['category', 'amount', 'date', 'description', 
                 'payment_method', 'is_recurring', 'receipt_image']

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']