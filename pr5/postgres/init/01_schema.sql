-- ПР5 (Варіант 3: Зливові колектори). Схема бази даних.

CREATE TABLE storm_drains (
    ts        timestamptz NOT NULL,
    station   text        NOT NULL,
    h         real        NOT NULL CHECK (h BETWEEN 0 AND 300),
    h_ema     real        NOT NULL,
    v         real        NOT NULL,
    v_ema     real        NOT NULL,
    alarm     smallint    NOT NULL CHECK (alarm IN (0, 1)),
    lag_ms    integer     NOT NULL,
    PRIMARY KEY (station, ts)
);

CREATE INDEX storm_drains_ts_idx ON storm_drains (ts);

CREATE TABLE station_status (
    ts      timestamptz NOT NULL DEFAULT now(),
    station text        NOT NULL,
    online  smallint    NOT NULL CHECK (online IN (0, 1))
);

CREATE INDEX station_status_ts_idx ON station_status (ts);