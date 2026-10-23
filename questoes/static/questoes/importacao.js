'use strict';
(() => {
    const form = document.getElementById('selecao-importacao');
    if (!form) return;
    const boxes = [...form.querySelectorAll('input[name="marcadas"]')];
    const counter = document.getElementById('contador-selecao');
    const outside = Number(counter.dataset.fora) - Number(counter.dataset.visiveis);
    const update = () => { counter.textContent = `${outside + boxes.filter(box => box.checked).length} selecionadas`; };
    boxes.forEach(box => box.addEventListener('change', update));
    form.querySelectorAll('[data-selecao]').forEach(button => button.addEventListener('click', () => {
        boxes.forEach(box => { box.checked = button.dataset.selecao === 'todas'; });
        update();
    }));
    update();
})();
