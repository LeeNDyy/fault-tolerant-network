# Отказоустойчивая сеть в Docker Compose

Лабораторный стенд запускается целиком в Linux-контейнерах. Два маршрутизатора на Keepalived реализуют VRRP, а ISC DHCP Relay пересылает запросы VLAN 30 обеим нодам Kea. PostgreSQL работает под Patroni с кворумом etcd. HAProxy подключает Kea и Stork к текущему лидеру.

| Сегмент | Адреса и подключение |
| --- | --- |
| VLAN 10 | VIP `192.168.10.1`, маршрутизаторы `.2/.3`, Kea `.11/.12`, пул `.100–.200` |
| VLAN 30 | VIP `192.168.30.1`, маршрутизаторы `.2/.3`, TFTP/HTTP `.14`, пул `.100–.200` |
| OVS | Аплинк и порты 2/3 пропускают теги 10/20/30. Порт 4 — access VLAN 10, порт 5 — access VLAN 30. Интерфейс `vlan10-mgmt` получает адрес по DHCP. |
| Backend | Приватная сеть `172.29.100.0/24` для PostgreSQL, etcd, HAProxy, Stork и обмена Kea HA. |
| Режим Kea | Hot standby, единая база аренд в PostgreSQL, репликация аренд средствами Patroni. |

VLAN 20 служит для проверки конфигурации транка. DHCP и маршрутизация настроены для VLAN 10 и VLAN 30. Compose создаёт отдельный L2-сегмент на каждый клиентский порт.

## Запуск

Нужны Linux Docker Engine с rootful bridge networking, Docker Compose 2.36+ и `/dev/net/tun` на хосте Docker. OVS использует userspace datapath. Для сборки требуется доступ к Debian, Alpine, ISC Cloudsmith и реестрам образов.

```sh
cp .env.example .env
```

Заполни четыре пароля в `.env`. Для каждого используй отдельную случайную строку длиной от 20 символов из `A–Z`, `a–z`, `0–9`. Затем выполни:

```sh
docker compose config -q
docker compose up -d --build
docker compose ps -a
```

На старте `db-init` ждёт доступности лидера и создаёт базы Kea и Stork. Успешный код выхода `db-init` — 0. Первому запуску нужно время на загрузку образов, bootstrap и подключение ведомых PostgreSQL.

- Stork доступен на `http://127.0.0.1:8080`. Первый вход — `admin` / `admin`. Сразу смени пароль. В **Services → Machines → Unauthorized** подтверди заявки от `kea-primary` и `kea-standby`, сверив токены с журналами контейнеров. [Документация Stork](https://stork.readthedocs.io/en/stable/install.html)
- Prometheus доступен на `http://127.0.0.1:9090/targets`. Метрики Kea отдают встроенные экспортёры агентов Stork на порту 9547. [Параметры экспортёра](https://stork.readthedocs.io/en/stable/man/stork-agent.8.html)
- По умолчанию включён `DHCP_MODE=relay`. Для прямой выдачи в VLAN 30 укажи `DHCP_MODE=direct` и повтори `docker compose up -d`. Compose пересоздаст маршрутизаторы и Kea с новой конфигурацией.

## Проверки

### VLAN и DHCP

```sh
docker compose exec ovs ovs-vsctl show
docker compose exec ovs ip -4 addr show dev vlan10-mgmt
docker compose exec alpine-1 ip -4 addr show dev link0.10
docker compose exec alpine-2 ip -4 addr show dev link0.10
docker compose exec alpine-3 ip -4 addr show dev link0
docker compose exec pxe-client ip -4 addr show dev link0
```

Клиенты Alpine и OVS должны получить адреса из пула VLAN 10, а `pxe-client` — из пула VLAN 30.

### PXE

```sh
docker compose exec pxe-client pxe-check
docker compose run --rm --no-deps -e PXE_STAGE=uefi pxe-client check
docker compose run --rm --no-deps -e PXE_STAGE=ipxe pxe-client check
```

Проверки сравнивают полученные DHCP-параметры с ожидаемыми, скачивают оба загрузчика через TFTP и проверяют доступность файлов Alpine через HTTP. В режиме `relay` тот же запрос проходит через текущий VRRP Master. PXE-сервер раздаёт netboot Alpine x86_64 и overlay с установщиком. Установщик рассчитан на пустой диск, указанный в `images/pxe/answers`. Проверка внутри Compose заканчивается на уровне DHCP/TFTP/HTTP. Загрузка ядра и установка на диск требуют PXE-клиента с собственным ядром и диском, которых у обычного контейнера нет. [Файлы Alpine netboot](https://dl-cdn.alpinelinux.org/alpine/v3.22/releases/x86_64/netboot-3.22.8/)

### VRRP

В первом терминале оставь пинг:

```sh
docker compose exec alpine-3 ping 192.168.10.1
```

Во втором останови основной маршрутизатор, проверь VIP на резервном и повтори запрос нового PXE-клиента:

```sh
docker compose stop router-1
docker compose logs --since 1m router-2
docker compose exec router-2 ip -br -4 addr
docker compose run --rm --no-deps pxe-client check
docker compose start router-1
```

### Kea HA

```sh
docker compose stop kea-primary
docker compose logs --follow kea-standby
```

Когда резервная нода перейдёт в `partner-down`, в другом терминале проверь выдачу новой аренды:

```sh
docker compose run --rm --no-deps pxe-client check
docker compose start kea-primary
```

`max-unacked-clients=0` ускоряет испытание остановки ноды. Изолируй этот сценарий от испытаний сетевых разделений, при которых потеря HA-связи может привести к одновременной выдаче на обеих нодах. [Особенности общей базы аренд](https://kb.isc.org/docs/kea-unique-databases)

### PostgreSQL HA

```sh
docker compose exec pg1 patronictl -c /run/patroni/config.yml list
docker compose exec etcd1 /usr/local/bin/etcdctl --endpoints=http://etcd1:2379,http://etcd2:2379,http://etcd3:2379 endpoint health
```

Подожди, пока появится синхронная реплика. Останови текущего лидера по его имени из списка. Пример ниже предполагает, что лидером был `pg1`.

```sh
docker compose stop pg1
docker compose exec pg2 patronictl -c /run/patroni/config.yml list
docker compose run --rm --no-deps pxe-client check
docker compose start pg1
```

Повтори проверку после избрания нового лидера. HAProxy переподключает приложения к новому лидеру. Запросы, захваченные переключением, могут оборваться. В строгом синхронном режиме PostgreSQL приостанавливает запись без синхронной реплики. Испытания моделируют отказы отдельных контейнеров на одном хосте.

Для завершения работы используй `docker compose down`. Именованные тома сохраняют данные PostgreSQL, etcd и мониторинга.
