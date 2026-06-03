import React, { useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  Building2,
  CheckCircle2,
  Database,
  FileText,
  Loader2,
  Lock,
  LockOpen,
  RefreshCw,
  ShieldCheck,
  TrendingUp,
  X,
  XCircle,
} from 'lucide-react';

type XmlParty = {
  ruc?: string;
  razon_social?: string;
  name?: string;
  direccion?: string;
};

type XmlItem = {
  codigo?: string;
  descripcion?: string;
  quantity?: number;
  cantidad?: number;
  unit_price?: number;
  precio_unitario?: number;
  total?: number;
};

export type AuditXmlPayload = {
  document_id?: string;
  emisor?: XmlParty;
  receptor?: XmlParty;
  items?: XmlItem[];
  raw_xml?: string;
};

export type AuditMovement = {
  id: string;
  date: string;
  voucher: string;
  glosa?: string;
  debit: number;
  credit: number;
  balance: number;
  ruc?: string;
  counterparty_name?: string;
  taxpayer_status?: string;
  hash?: string;
  previous_hash?: string;
  hash_valid?: boolean;
  hash_chain_valid?: boolean;
  xml?: AuditXmlPayload;
};

export type AuditAccountData = {
  ok?: boolean;
  tenant_id?: string;
  code?: string;
  account_id?: string;
  account_code?: string;
  name?: string;
  period?: string;
  current_balance?: number;
  movements?: AuditMovement[];
  recommendations?: string[];
};

type AuditDrillDownProps = {
  isOpen: boolean;
  onClose: () => void;
  accountId?: string;
  tenantId?: string;
  apiBaseUrl?: string;
  accountData?: AuditAccountData | null;
  onError?: (message: string) => void;
};

type AuditOpenOptions = {
  tenantId?: string;
  apiBaseUrl?: string;
};

const moneyFormatter = new Intl.NumberFormat('es-PE', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const formatMoney = (value: number | undefined) => moneyFormatter.format(Number(value || 0));

const shortHash = (hash?: string) => {
  if (!hash) return 'Sin hash';
  return hash.length > 18 ? `${hash.slice(0, 10)}...${hash.slice(-6)}` : hash;
};

const statusClassName = (status?: string) => {
  const value = (status || 'PENDIENTE').toUpperCase();
  if (value === 'HABIDO' || value === 'ACTIVO') {
    return 'border-emerald-200 bg-emerald-50 text-emerald-700';
  }
  if (value === 'NO HABIDO' || value === 'BAJA') {
    return 'border-rose-200 bg-rose-50 text-rose-700';
  }
  return 'border-amber-200 bg-amber-50 text-amber-700';
};

const partyName = (party?: XmlParty) => party?.razon_social || party?.name || 'No informado';

export const loadAnalyticLedger = async (
  accountId: string,
  options: AuditOpenOptions = {},
) => {
  const params = new URLSearchParams();
  if (options.tenantId) params.set('tenant_id', options.tenantId);

  const baseUrl = (options.apiBaseUrl || '').replace(/\/$/, '');
  const query = params.toString();
  const response = await fetch(
    `${baseUrl}/api/ledger/analytic/${encodeURIComponent(accountId)}${query ? `?${query}` : ''}`,
    {
      headers: options.tenantId ? { 'X-Tenant-Id': options.tenantId } : undefined,
    },
  );

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || payload.error || `No se pudo cargar la cuenta ${accountId}`);
  }

  return (await response.json()) as AuditAccountData;
};

export const onCellClick = async (
  code: string,
  setSelectedAccount: (data: AuditAccountData) => void,
  setIsDrawerOpen: (isOpen: boolean) => void,
  tenantId = '20601234567',
  apiBaseUrl = '',
) => {
  const data = await loadAnalyticLedger(code, { tenantId, apiBaseUrl });
  setSelectedAccount(data);
  setIsDrawerOpen(true);
  return data;
};

export const AuditInteractiveCell = ({
  accountId,
  active = false,
  children,
  className = '',
  onOpen,
}: {
  accountId: string;
  active?: boolean;
  children: React.ReactNode;
  className?: string;
  onOpen: (accountId: string) => void;
}) => (
  <button
    type="button"
    onClick={() => onOpen(accountId)}
    className={[
      'w-full rounded-md px-2 py-1 text-left transition-all duration-150',
      'hover:bg-white/85 hover:text-blue-700 hover:shadow-sm active:scale-[0.99]',
      active ? 'bg-blue-50 text-blue-700 ring-1 ring-blue-200' : '',
      className,
    ].join(' ')}
  >
    {children}
  </button>
);

const XmlModal = ({
  movement,
  onClose,
}: {
  movement: AuditMovement | null;
  onClose: () => void;
}) => {
  if (!movement) return null;

  const xml = movement.xml || {};
  const items = xml.items || [];

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-950/45 p-4 backdrop-blur-sm">
      <div className="max-h-[88vh] w-full max-w-3xl overflow-hidden rounded-xl border border-white/70 bg-white/95 shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50/90 px-5 py-4">
          <div className="min-w-0">
            <p className="text-[10px] font-black uppercase tracking-[0.2em] text-blue-600">XML original</p>
            <h3 className="truncate text-lg font-black tracking-tight text-slate-900">{movement.voucher}</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar XML"
            className="rounded-full p-2 text-slate-500 transition-colors hover:bg-slate-200 hover:text-slate-900"
          >
            <X size={18} />
          </button>
        </div>

        <div className="max-h-[72vh] space-y-4 overflow-y-auto bg-[#f0f2f5] p-5 font-['Inter',sans-serif]">
          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded-lg border border-white/70 bg-white/80 p-4 shadow-sm backdrop-blur">
              <div className="mb-2 flex items-center gap-2 text-xs font-black uppercase text-slate-500">
                <Building2 size={14} />
                Emisor
              </div>
              <p className="text-sm font-bold text-slate-900">{partyName(xml.emisor)}</p>
              <p className="mt-1 text-xs text-slate-500">RUC {xml.emisor?.ruc || 'No informado'}</p>
            </div>
            <div className="rounded-lg border border-white/70 bg-white/80 p-4 shadow-sm backdrop-blur">
              <div className="mb-2 flex items-center gap-2 text-xs font-black uppercase text-slate-500">
                <Building2 size={14} />
                Receptor
              </div>
              <p className="text-sm font-bold text-slate-900">{partyName(xml.receptor)}</p>
              <p className="mt-1 text-xs text-slate-500">RUC {xml.receptor?.ruc || 'No informado'}</p>
            </div>
          </div>

          <div className="overflow-hidden rounded-lg border border-white/70 bg-white/85 shadow-sm backdrop-blur">
            <table className="w-full text-[11px]">
              <thead className="bg-slate-100 text-slate-500">
                <tr>
                  <th className="px-3 py-2 text-left">Codigo</th>
                  <th className="px-3 py-2 text-left">Item</th>
                  <th className="px-3 py-2 text-right">Cant.</th>
                  <th className="px-3 py-2 text-right">P. Unit.</th>
                  <th className="px-3 py-2 text-right">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {items.map((item, index) => (
                  <tr key={`${item.codigo || 'item'}-${index}`}>
                    <td className="px-3 py-2 font-mono text-slate-500">{item.codigo || '-'}</td>
                    <td className="px-3 py-2 font-semibold text-slate-800">{item.descripcion || '-'}</td>
                    <td className="px-3 py-2 text-right font-mono">{item.cantidad || item.quantity || 0}</td>
                    <td className="px-3 py-2 text-right font-mono">{formatMoney(item.precio_unitario || item.unit_price)}</td>
                    <td className="px-3 py-2 text-right font-mono font-bold">{formatMoney(item.total)}</td>
                  </tr>
                ))}
                {items.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-3 py-6 text-center text-xs font-semibold text-slate-400">
                      XML sin items normalizados.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <pre className="max-h-48 overflow-auto rounded-lg border border-slate-200 bg-slate-950 p-4 text-[10px] leading-relaxed text-slate-100">
            {xml.raw_xml || 'Sin XML crudo disponible'}
          </pre>
        </div>
      </div>
    </div>
  );
};

export const AuditDrillDown = ({
  isOpen,
  onClose,
  accountId,
  tenantId,
  apiBaseUrl = '',
  accountData,
  onError,
}: AuditDrillDownProps) => {
  const [data, setData] = useState<AuditAccountData | null>(accountData || null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeMovementId, setActiveMovementId] = useState('');
  const [xmlMovement, setXmlMovement] = useState<AuditMovement | null>(null);

  const resolvedAccountId = accountId || accountData?.account_id || accountData?.account_code || accountData?.code || '';

  useEffect(() => {
    if (!isOpen) return;
    if (accountData && !accountId) {
      setData(accountData);
      setError('');
      setLoading(false);
      return;
    }
    if (!resolvedAccountId) return;

    let cancelled = false;
    setLoading(true);
    setError('');

    loadAnalyticLedger(resolvedAccountId, { tenantId, apiBaseUrl })
      .then((payload) => {
        if (!cancelled) setData(payload);
      })
      .catch((err: Error) => {
        const message = err.message || 'No se pudo cargar el drill-down';
        if (!cancelled) {
          setError(message);
          onError?.(message);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [accountData, accountId, apiBaseUrl, isOpen, onError, resolvedAccountId, tenantId]);

  const movements = data?.movements || [];
  const accountCode = data?.code || data?.account_code || data?.account_id || resolvedAccountId;
  const currentBalance = formatMoney(data?.current_balance ?? movements[movements.length - 1]?.balance ?? 0);
  const invalidHashes = useMemo(() => movements.filter((movement) => !movement.hash_valid).length, [movements]);
  const criticalRucs = useMemo(
    () => movements.filter((movement) => ['NO HABIDO', 'BAJA'].includes((movement.taxpayer_status || '').toUpperCase())).length,
    [movements],
  );
  const reloadLedger = () => {
    if (!resolvedAccountId) return;
    setLoading(true);
    setError('');
    loadAnalyticLedger(resolvedAccountId, { tenantId, apiBaseUrl })
      .then(setData)
      .catch((err: Error) => {
        const message = err.message || 'No se pudo recargar el drill-down';
        setError(message);
        onError?.(message);
      })
      .finally(() => setLoading(false));
  };

  if (!isOpen) return null;

  return (
    <>
      <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/35 font-['Inter',sans-serif] backdrop-blur-sm">
        <div className="h-full w-full overflow-hidden bg-[#f0f2f5] shadow-2xl sm:max-w-[1040px]">
          <div className="flex h-full flex-col border-l border-white/70 bg-white/45 backdrop-blur-xl">
            <header className="border-b border-white/70 bg-white/75 px-5 py-4 shadow-sm backdrop-blur-xl">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <p className="text-[10px] font-black uppercase tracking-[0.24em] text-blue-600">
                    Auditoria Forense Interactiva
                  </p>
                  <h2 className="mt-1 truncate text-xl font-black tracking-tight text-slate-900">
                    Cuenta {accountCode || '-'} - {data?.name || 'Libro Mayor Analitico'}
                  </h2>
                  <p className="mt-1 text-xs font-semibold text-slate-500">
                    Periodo {data?.period || 'actual'} - Tenant {tenantId || data?.tenant_id || 'activo'}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={reloadLedger}
                    className="rounded-lg border border-slate-200 bg-white/80 p-2 text-slate-500 shadow-sm transition-colors hover:bg-white hover:text-blue-700 active:scale-95"
                    aria-label="Recargar auditoria"
                  >
                    <RefreshCw size={17} />
                  </button>
                  <button
                    type="button"
                    onClick={onClose}
                    aria-label="Cerrar auditoria"
                    className="rounded-lg border border-slate-200 bg-white/80 p-2 text-slate-500 shadow-sm transition-colors hover:bg-white hover:text-slate-900 active:scale-95"
                  >
                    <X size={18} />
                  </button>
                </div>
              </div>

              <div className="mt-4 grid gap-3 md:grid-cols-4">
                <div className="rounded-lg border border-white/70 bg-white/75 p-3 shadow-sm backdrop-blur">
                  <p className="text-[10px] font-black uppercase text-slate-400">Saldo acumulado</p>
                  <p className="mt-1 text-lg font-black text-slate-900">{currentBalance}</p>
                </div>
                <div className="rounded-lg border border-white/70 bg-white/75 p-3 shadow-sm backdrop-blur">
                  <p className="text-[10px] font-black uppercase text-slate-400">Movimientos</p>
                  <p className="mt-1 text-lg font-black text-slate-900">{movements.length}</p>
                </div>
                <div className="rounded-lg border border-white/70 bg-white/75 p-3 shadow-sm backdrop-blur">
                  <p className="text-[10px] font-black uppercase text-slate-400">Hashes invalidos</p>
                  <p className={invalidHashes ? 'mt-1 text-lg font-black text-rose-700' : 'mt-1 text-lg font-black text-emerald-700'}>
                    {invalidHashes}
                  </p>
                </div>
                <div className="rounded-lg border border-white/70 bg-white/75 p-3 shadow-sm backdrop-blur">
                  <p className="text-[10px] font-black uppercase text-slate-400">RUC critico</p>
                  <p className={criticalRucs ? 'mt-1 text-lg font-black text-rose-700' : 'mt-1 text-lg font-black text-emerald-700'}>
                    {criticalRucs}
                  </p>
                </div>
              </div>
            </header>

            <main className="flex-1 overflow-y-auto p-5">
              {loading && (
                <div className="flex h-48 items-center justify-center rounded-xl border border-white/70 bg-white/70 text-sm font-bold text-slate-500 shadow-sm backdrop-blur">
                  <Loader2 className="mr-2 animate-spin" size={18} />
                  Cargando Libro Mayor Analitico...
                </div>
              )}

              {error && !loading && (
                <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm font-semibold text-rose-700">
                  <AlertTriangle className="mr-2 inline" size={17} />
                  {error}
                </div>
              )}

              {!loading && !error && (
                <div className="space-y-5">
                  <section className="overflow-hidden rounded-xl border border-white/70 bg-white/75 shadow-sm backdrop-blur">
                    <div className="flex items-center justify-between border-b border-slate-200/80 px-4 py-3">
                      <div className="flex items-center gap-2 text-xs font-black uppercase tracking-wider text-slate-600">
                        <Database size={15} />
                        Libro Mayor Analitico
                      </div>
                      <div className="flex items-center gap-2 text-[10px] font-bold text-slate-500">
                        <ShieldCheck size={14} className="text-emerald-600" />
                        RLS activo por tenant
                      </div>
                    </div>

                    <div className="overflow-x-auto">
                      <table className="w-full min-w-[920px] text-[11px]">
                        <thead className="bg-slate-100/80 text-slate-500">
                          <tr className="font-black uppercase">
                            <th className="px-3 py-2 text-left">Fecha</th>
                            <th className="px-3 py-2 text-left">Voucher/XML</th>
                            <th className="px-3 py-2 text-left">Glosa</th>
                            <th className="px-3 py-2 text-left">RUC</th>
                            <th className="px-3 py-2 text-right">Debe</th>
                            <th className="px-3 py-2 text-right">Haber</th>
                            <th className="px-3 py-2 text-right">Saldo</th>
                            <th className="px-3 py-2 text-left">Hash</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {movements.map((movement) => {
                            const active = activeMovementId === movement.id;
                            return (
                              <tr
                                key={movement.id || movement.voucher}
                                onClick={() => setActiveMovementId(movement.id)}
                                className={[
                                  'cursor-default transition-colors',
                                  active ? 'bg-blue-50/80' : 'hover:bg-white/90',
                                ].join(' ')}
                              >
                                <td className="px-3 py-2 font-mono text-slate-500">{movement.date}</td>
                                <td className="px-3 py-2">
                                  <button
                                    type="button"
                                    onClick={(event) => {
                                      event.stopPropagation();
                                      setXmlMovement(movement);
                                    }}
                                    className="inline-flex items-center gap-1 rounded-md px-2 py-1 font-black text-blue-700 transition-colors hover:bg-blue-50 active:bg-blue-100"
                                  >
                                    <FileText size={13} />
                                    {movement.voucher || 'Ver XML'}
                                  </button>
                                </td>
                                <td className="max-w-[260px] truncate px-3 py-2 font-semibold text-slate-700" title={movement.glosa}>
                                  {movement.glosa || '-'}
                                </td>
                                <td className="px-3 py-2">
                                  <div className="flex flex-col gap-1">
                                    <span className="font-mono font-bold text-slate-700">{movement.ruc || '-'}</span>
                                    <span className={`w-fit rounded-full border px-2 py-0.5 text-[9px] font-black ${statusClassName(movement.taxpayer_status)}`}>
                                      {movement.taxpayer_status || 'PENDIENTE'}
                                    </span>
                                  </div>
                                </td>
                                <td className="px-3 py-2 text-right font-mono text-slate-700">{formatMoney(movement.debit)}</td>
                                <td className="px-3 py-2 text-right font-mono text-slate-700">{formatMoney(movement.credit)}</td>
                                <td className="px-3 py-2 text-right font-mono font-black text-slate-900">{formatMoney(movement.balance)}</td>
                                <td className="px-3 py-2">
                                  <div className="flex items-center gap-2">
                                    {movement.hash_valid ? (
                                      <Lock size={14} className="text-emerald-600" />
                                    ) : (
                                      <LockOpen size={14} className="text-rose-600" />
                                    )}
                                    <span className="font-mono text-[10px] text-slate-500">{shortHash(movement.hash)}</span>
                                  </div>
                                </td>
                              </tr>
                            );
                          })}
                          {movements.length === 0 && (
                            <tr>
                              <td colSpan={8} className="px-3 py-12 text-center text-xs font-bold text-slate-400">
                                <FileText size={24} className="mx-auto mb-2" />
                                Sin movimientos para esta cuenta.
                              </td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                  </section>

                  <section className="grid gap-4 lg:grid-cols-[1fr_320px]">
                    <div className="rounded-xl border border-slate-800 bg-slate-950 p-5 text-slate-200 shadow-sm">
                      <div className="mb-3 flex items-center gap-2 text-blue-300">
                        <TrendingUp size={18} />
                        <span className="text-xs font-black uppercase tracking-wider">IA Auditora: Recomendaciones</span>
                      </div>
                      <ul className="space-y-2 text-xs leading-relaxed">
                        {(data?.recommendations || ['Sin recomendaciones generadas.']).map((item) => (
                          <li key={item} className="flex gap-2">
                            <CheckCircle2 size={14} className="mt-0.5 shrink-0 text-blue-300" />
                            <span>{item}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div className="rounded-xl border border-white/70 bg-white/75 p-5 shadow-sm backdrop-blur">
                      <div className="mb-3 flex items-center gap-2 text-xs font-black uppercase text-slate-600">
                        <ShieldCheck size={16} />
                        Inmutabilidad
                      </div>
                      <div className="space-y-3 text-xs font-semibold text-slate-600">
                        <div className="flex items-center justify-between">
                          <span>Cadena SHA-256</span>
                          {invalidHashes ? (
                            <XCircle size={17} className="text-rose-600" />
                          ) : (
                            <CheckCircle2 size={17} className="text-emerald-600" />
                          )}
                        </div>
                        <div className="flex items-center justify-between">
                          <span>RUC Habido/No Habido</span>
                          {criticalRucs ? (
                            <AlertTriangle size={17} className="text-amber-600" />
                          ) : (
                            <CheckCircle2 size={17} className="text-emerald-600" />
                          )}
                        </div>
                        <div className="rounded-lg bg-slate-100 p-3 font-mono text-[10px] text-slate-500">
                          SET LOCAL app.tenant_id = tenant activo
                        </div>
                      </div>
                    </div>
                  </section>
                </div>
              )}
            </main>
          </div>
        </div>
      </div>

      <XmlModal movement={xmlMovement} onClose={() => setXmlMovement(null)} />
    </>
  );
};

export default AuditDrillDown;
