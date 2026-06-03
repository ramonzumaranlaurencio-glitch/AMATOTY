import { useMemo, useState } from 'react';
import { Activity, Building2, FileSearch, ShieldCheck } from 'lucide-react';
import { AuditDrillDown, AuditInteractiveCell } from '@audit';

type TrialBalanceRow = {
  code: string;
  name: string;
  debit: number;
  credit: number;
};

const rows: TrialBalanceRow[] = [
  { code: '12.1', name: 'Cuentas por cobrar comerciales', debit: 248900.4, credit: 94320.1 },
  { code: '40.1', name: 'Tributos por pagar IGV', debit: 72500, credit: 118430.55 },
  { code: '42.1', name: 'Cuentas por pagar comerciales', debit: 63110.2, credit: 199200.9 },
  { code: '70.1', name: 'Ventas gravadas', debit: 0, credit: 486920.76 },
  { code: '69.1', name: 'Costo de ventas', debit: 301880.6, credit: 0 },
];

const money = new Intl.NumberFormat('es-PE', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export default function App() {
  const [tenantId, setTenantId] = useState('20601234567');
  const [selectedAccountId, setSelectedAccountId] = useState('');
  const [drawerOpen, setDrawerOpen] = useState(false);

  const totals = useMemo(
    () =>
      rows.reduce(
        (acc, row) => {
          acc.debit += row.debit;
          acc.credit += row.credit;
          return acc;
        },
        { debit: 0, credit: 0 },
      ),
    [],
  );

  const openAccount = (accountId: string) => {
    setSelectedAccountId(accountId);
    setDrawerOpen(true);
  };

  return (
    <main className="min-h-screen bg-[#f0f2f5] p-4 font-sans text-slate-900 md:p-8">
      <div className="mx-auto max-w-7xl space-y-5">
        <header className="flex flex-col gap-4 rounded-xl border border-white/70 bg-white/65 p-5 shadow-sm backdrop-blur-xl md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-[10px] font-black uppercase tracking-[0.24em] text-blue-600">
              CONTA_PRO Enterprise
            </p>
            <h1 className="mt-1 text-2xl font-black tracking-tight">Auditoria Forense Interactiva</h1>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <label className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white/80 px-3 py-2 text-xs font-bold text-slate-600 shadow-sm">
              <Building2 size={15} className="text-blue-700" />
              <input
                value={tenantId}
                onChange={(event) => setTenantId(event.target.value)}
                className="w-32 bg-transparent font-mono text-slate-900 outline-none"
                aria-label="Tenant activo"
              />
            </label>
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-black text-emerald-700">
              RLS activo
            </div>
          </div>
        </header>

        <section className="grid gap-3 md:grid-cols-3">
          <div className="rounded-xl border border-white/70 bg-white/70 p-4 shadow-sm backdrop-blur">
            <div className="flex items-center gap-2 text-xs font-black uppercase text-slate-500">
              <Activity size={15} />
              Debe
            </div>
            <p className="mt-2 text-xl font-black">{money.format(totals.debit)}</p>
          </div>
          <div className="rounded-xl border border-white/70 bg-white/70 p-4 shadow-sm backdrop-blur">
            <div className="flex items-center gap-2 text-xs font-black uppercase text-slate-500">
              <Activity size={15} />
              Haber
            </div>
            <p className="mt-2 text-xl font-black">{money.format(totals.credit)}</p>
          </div>
          <div className="rounded-xl border border-white/70 bg-white/70 p-4 shadow-sm backdrop-blur">
            <div className="flex items-center gap-2 text-xs font-black uppercase text-slate-500">
              <ShieldCheck size={15} />
              Diferencia
            </div>
            <p className="mt-2 text-xl font-black">{money.format(totals.debit - totals.credit)}</p>
          </div>
        </section>

        <section className="overflow-hidden rounded-xl border border-white/70 bg-white/75 shadow-sm backdrop-blur">
          <div className="flex items-center justify-between border-b border-slate-200/80 px-4 py-3">
            <div className="flex items-center gap-2 text-xs font-black uppercase tracking-wider text-slate-600">
              <FileSearch size={15} />
              Matriz de cuentas auditables
            </div>
            <span className="text-[10px] font-bold uppercase text-slate-400">Periodo Mayo 2026</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[820px] text-[12px]">
              <thead className="bg-slate-100/80 text-slate-500">
                <tr className="font-black uppercase">
                  <th className="px-3 py-2 text-left">Cuenta</th>
                  <th className="px-3 py-2 text-left">Nombre</th>
                  <th className="px-3 py-2 text-right">Debe</th>
                  <th className="px-3 py-2 text-right">Haber</th>
                  <th className="px-3 py-2 text-right">Saldo</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rows.map((row) => {
                  const active = selectedAccountId === row.code && drawerOpen;
                  return (
                    <tr key={row.code} className="transition-colors hover:bg-white/90">
                      <td className="px-3 py-2">
                        <AuditInteractiveCell accountId={row.code} active={active} onOpen={openAccount}>
                          <span className="font-mono font-black">{row.code}</span>
                        </AuditInteractiveCell>
                      </td>
                      <td className="px-3 py-2">
                        <AuditInteractiveCell accountId={row.code} active={active} onOpen={openAccount}>
                          <span className="font-bold">{row.name}</span>
                        </AuditInteractiveCell>
                      </td>
                      <td className="px-3 py-2 text-right">
                        <AuditInteractiveCell accountId={row.code} active={active} className="text-right" onOpen={openAccount}>
                          <span className="font-mono">{money.format(row.debit)}</span>
                        </AuditInteractiveCell>
                      </td>
                      <td className="px-3 py-2 text-right">
                        <AuditInteractiveCell accountId={row.code} active={active} className="text-right" onOpen={openAccount}>
                          <span className="font-mono">{money.format(row.credit)}</span>
                        </AuditInteractiveCell>
                      </td>
                      <td className="px-3 py-2 text-right">
                        <AuditInteractiveCell accountId={row.code} active={active} className="text-right" onOpen={openAccount}>
                          <span className="font-mono font-black">{money.format(row.debit - row.credit)}</span>
                        </AuditInteractiveCell>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <AuditDrillDown
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        accountId={selectedAccountId}
        tenantId={tenantId}
      />
    </main>
  );
}
