# Ouro Widget

Widget de desktop em Python que mostra o preço do ouro (spot) em tempo real,
com cotações internacionais e da China.

## Recursos

- Spot USD/BRL com cadeia de fallback (goldprice.dev → Sina → goldprice.org)
- Câmbio: awesomeapi → currency-api (jsDelivr) → open.er-api.com
- Baseline PAXG: Binance → OKX
- Bolsas chinesas: SGE (Au99.99, Au(T+D)) e futuro SHFE via Sina/Eastmoney
- Base China Gold (jijinhao JO_52683) e barras de ouro de banco (xxapi)
- Cache local, tolerância a 429 e modo `--dump` (sem interface)

## Uso

```bash
python3 gold_widget.py
```

## Licença

Uso pessoal.
