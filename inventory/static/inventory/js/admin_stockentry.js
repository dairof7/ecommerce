document.addEventListener('DOMContentLoaded', function() {
    // Django admin encloses jQuery in the django.jQuery namespace
    if (typeof django !== 'undefined' && django.jQuery) {
        var $ = django.jQuery;
        
        var productSelect = $('#id_product');
        var priceInput = $('#id_purchase_price');
        
        productSelect.on('change', function() {
            var productId = $(this).val();
            if (productId) {
                // Determine if we are on add or change page to build the relative URL
                var isAddPage = window.location.pathname.indexOf('/add/') !== -1;
                
                // Construct the URL to the custom admin view
                var url = isAddPage ? '../get_product_price/' + productId + '/' : '../../get_product_price/' + productId + '/';
                
                $.ajax({
                    url: url,
                    type: 'GET',
                    success: function(response) {
                        if (response.purchase_price !== undefined) {
                            priceInput.val(response.purchase_price);
                        }
                    },
                    error: function(error) {
                        console.error('Error fetching product price:', error);
                    }
                });
            }
        });
    }
});
