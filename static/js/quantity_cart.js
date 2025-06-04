function handleQuantityChange(select, index) {
    const wrapper = select.closest('.custom-select-wrapper');
    const input = wrapper.querySelector('input[type="number"]');

    if (select.value === "custom") {
        input.style.display = 'block';
        input.focus();
    } else {
        input.style.display = 'none';
        wrapper.closest('form').submit();
    }
}
