async page => {
  // Executado por playwright-cli run-code --filename=validacao_relacionados.js.
  // Valida a inscrição já aberta. Cancela todas as confirmações de remoção.
  const result = { url: page.url(), titulo: await page.title(), secoes: [] };
  const tab = page.getByRole('button', { name: 'Relacionados', exact: true });
  if (await tab.count()) await tab.click();
  else {
    await page.getByRole('button', { name: 'Mais abas' }).click();
    await page.getByRole('menuitem', { name: 'Relacionados', exact: true }).click();
  }
  for (const key of ['leads', 'pagamentos', 'redacoes', 'provas', 'avaliacoes', 'classificacoes', 'precos', 'termos']) {
    const section = page.locator(`article[data-section="${key}"]`);
    const entry = { secao: key, paginas: [], status: 'pendente' };
    result.secoes.push(entry);
    try {
      const toggle = section.locator('button.lead-rel-section__toggle');
      if (await toggle.getAttribute('aria-expanded') !== 'true') await toggle.click();
      let previousIds = null;
      for (let p = 1; p <= 100; p++) {
        await page.waitForFunction(({ key, previousIds }) => {
          const root = document.querySelector(`article[data-section="${key}"]`);
          const visible = el => el && getComputedStyle(el).visibility !== 'hidden' && el.getClientRects().length > 0;
          if (!root || visible(root.querySelector('.crm-data-grid__load-overlay'))) return false;
          const error = root.querySelector('.crm-data-grid__error, .lead-rel-error');
          if (visible(error) && error.textContent.trim()) return true;
          const ids = [...root.querySelectorAll('tbody tr[data-row-id]')].map(r => r.dataset.rowId);
          if (previousIds && JSON.stringify(ids) === previousIds) return false;
          return ids.length > 0 || visible(root.querySelector('.lead-rel-empty'));
        }, { key, previousIds }, { timeout: 20000 });
        const error = await section.locator('.crm-data-grid__error, .lead-rel-error').allTextContents();
        if (error.some(s => s.trim())) throw new Error(error.join(' '));
        const boxes = section.locator('input.crm-data-grid__row-select');
        const count = await boxes.count();
        const pageResult = { pagina: p, linhas: count, marcadas: 0, selecao_interna: 0, confirmacao: false };
        entry.paginas.push(pageResult);
        if (!count) { entry.status = 'vazia'; break; }
        const expectedIds = await boxes.evaluateAll(xs => xs.map(x => x.closest('tr').dataset.rowId));
        const initiallyChecked = await boxes.evaluateAll(xs => xs.map(x => x.checked));
        try {
          for (let i = 0; i < count; i++) await boxes.nth(i).check({ timeout: 5000 });
          const selected = await page.evaluate(() => window.EntityListRuntime.getGrid().getSelectedRowIds());
          pageResult.marcadas = await section.locator('input.crm-data-grid__row-select:checked').count();
          pageResult.selecao_interna = selected.length;
          pageResult.ids_correspondem = expectedIds.every(id => selected.includes(id)) && selected.length === expectedIds.length;
          if (pageResult.marcadas !== count || !pageResult.ids_correspondem) throw new Error('Seleção visual e interna divergentes');
          await section.locator('button.lead-rel-btn-remover').click({ timeout: 5000 });
          const dialog = page.getByRole('dialog').filter({ hasText: 'Tem certeza que deseja remover o relacionamento?' });
          await dialog.waitFor({ state: 'visible', timeout: 5000 });
          pageResult.confirmacao = await dialog.getByRole('button', { name: 'Remover', exact: true }).isVisible();
          await dialog.getByRole('button', { name: 'Cancelar', exact: true }).click();
        } finally {
          const dialog = page.getByRole('dialog').filter({ hasText: 'Tem certeza que deseja remover o relacionamento?' });
          if (await dialog.isVisible()) await dialog.getByRole('button', { name: 'Cancelar', exact: true }).click();
          for (let i = 0; i < count; i++) await boxes.nth(i).setChecked(initiallyChecked[i], { timeout: 5000 });
          pageResult.selecao_apos_restaurar = await page.evaluate(() => window.EntityListRuntime.getGrid().getSelectedRowIds().length);
        }
        const next = section.locator('button.crm-data-grid__next');
        pageResult.tem_proxima = await next.count() > 0 && await next.isEnabled();
        if (!pageResult.tem_proxima) { entry.status = 'validada'; break; }
        previousIds = JSON.stringify(expectedIds);
        await next.click();
        if (p === 100) throw new Error('Limite de 100 páginas atingido');
      }
    } catch (error) {
      entry.status = 'falha';
      entry.erro = String(error.message);
    }
  }
  return result;
}
