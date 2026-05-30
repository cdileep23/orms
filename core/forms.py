from django import forms
from core.models import OrderModel


class ProductOrderForm(forms.ModelForm):
    """
    ModelForm = a form auto-built from a model.
    Django reads the model fields listed below and generates the
    matching HTML widgets + validation for free.

    GOTCHA: the inner class MUST be named `Meta` (capital M).
    A lowercase `class meta:` is silently ignored — Django won't
    raise an error, the form just acts like no model was attached
    and you'll see "ModelForm has no model class specified."
    """
    class Meta:
        model = OrderModel
        fields = ('product', 'no_of_items')

    """
    clean_<fieldname>() — per-field validation.
    Runs AFTER the basic type/required checks pass.
    Returning the cleaned value is required so Django stores it.
    Raising ValidationError attaches the error message to the field.
    """
    def clean_no_of_items(self):
        no_of_items = self.cleaned_data['no_of_items']
        product = self.cleaned_data.get('product')

        """
        product may be None if the product field itself failed
        validation earlier (e.g. user picked nothing). Skip the
        stock check in that case — Django will already show the
        "this field is required" error on `product`.
        """
        if product and no_of_items > product.number_in_stock:
            raise forms.ValidationError(
                f"Only {product.number_in_stock} in stock — can't order {no_of_items}."
            )
        return no_of_items
