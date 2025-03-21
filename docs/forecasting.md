# Global Forecasting Walkthrough

## API Usage

All individual forecasters (e.g. `lasso` / `xgboost`) have the same API. Use `**kwargs` to pass custom hyperparameters into the underlying regressor (e.g. sklearn's `LinearRegression` regressor in functime's `linear_model` forecaster). AutoML forecasters (e.g. `auto_lasso` and `auto_xgboost`) follow a similar API design. View [API reference](/ref/forecasting/) for details.
## Supported Forecasters

`functime` currently supports the following autoregressive global forecasters.

??? info "Forecasters"

    - `ann`
    - `catboost`
    - `censored_model`
    - `elastic_net`
    - `flaml_lightgbm`
    - `knn`
    - `lasso`
    - `lightgbm`
    - `linear_model`
    - `ridge`
    - `xgboost`
    - `zero_inflated_model`

??? info "AutoML Forecasters"

    - `auto_elastic_net`
    - `auto_knn`
    - `auto_lasso`
    - `auto_lightgbm`
    - `auto_linear_model`
    - `auto_ridge`

## Quickstart

Want to go straight into code? Run through every forecasting example with the following script:

??? tip "`quickstart.py`"

    ```python
    --8<-- "docs/code/quickstart.py"
    ```

## Prepare Data

Load a collection of time series, also known as panel data, into a [`polars.LazyFrame`](https://pola-rs.github.io/polars/py-polars/html/reference/lazyframe/index.html) (recommended) or `polars.DataFrame` and split them into train/test subsets.

```python
# Load data
y = pl.read_parquet("c")
entity_col, time_col = y.columns[:2]
X = (
    y.select([entity_col, time_col])
    .pipe(add_calendar_effects(["month"]))
    .pipe(add_holiday_effects(country_codes=["US"], freq="1mo"))
    .collect()
)

# Train-test splits
test_size = 3
freq = "1mo"
y_train, y_test = train_test_split(test_size)(y)
X_train, X_test = train_test_split(test_size)(X)
```

!!! info "Supported Data Schemas"

    `X: polars.LazyFrame | polars.DataFrame` and `y: polars.LazyFrame | polars.DataFrame` must contain at least three columns.
    The first column must represent the `entity` / `series_id` dimension.
    The second column must represent the `time` dimension as an integer, `pl.Date`, or `pl.Datetime` series.
    Remaining columns are considered as features.

## Fit / Predict / Score

`functime` forecasters expose sklearn-compatible `.fit` and `.predict` methods.
`functime.metrics` contains a comprehensive range of scoring functions for both point and probablistic forecasts.

??? info "Supported Forecast Metrics"

```python
from functime.forecasting import linear_model
from functime.metrics import mase

# Fit
forecaster = linear_model(lags=24, freq="1mo")
forecaster.fit(y=y_train)

# Predict
y_pred = forecaster.predict(fh=3)

# Score
scores = mase(y_true=y_test, y_pred=y_pred, y_train=y_train)
```

!!! info "Supported Data Schemas"

    `X: polars.LazyFrame | polars.DataFrame` and `y: polars.LazyFrame | polars.DataFrame` must contain at least three columns.
    The first column must represent the `entity` / `series_id` dimension.
    The second column must represent the `time` dimension as an integer, `pl.Date`, or `pl.Datetime` series.
    Remaining columns are considered as features.

!!! tip "functime ❤️ currying"

    Every `transformer` and `splitter` are [curried functions](https://composingprograms.com/pages/16-higher-order-functions.html#currying).

    ```python
    from functime.preprocessing import boxcox, impute

    # Use df.pipe to chain operations together
    X_new: pl.LazyFrame = (
        X.pipe(boxcox(method="mle"))
        .pipe(impute(method="linear"))
    )
    # Call .collect to execute query
    X_new = X_splits.collect()
    ```

    You can also use any `forecaster` as a curried function to run fit-predict in a single line of code.

    ```python
    from functime.forecasting import linear_model

    y_pred = linear_model(lags=24, freq="1mo")(
        y=y_train,
        fh=28,
        X=X_train,
        X_future=X_test
    )
    ```

!!! warning "functime is lazy"

    `transformers` and `splitters` in `cross_validation`, `feature_extraction`, and `preprocessing` are lazy.
    These callables return `LazyFrames`, which represents a Lazy computation graph/query against the input `DataFrame` / `LazyFrame`.
    **No computation is run until the `collect()` method is called on the `LazyFrame`.**

    `X` and `y` should be preprocessed lazily for optimal performance.
    Lazy evaluation allows `polars` to optimize all operations on the input `DataFrame` / `LazyFrame` at once.
    Lazy preprocessing in `functime` allows for more efficient `groupby` operations.

    With lazy transforms, operations series-by-series (e.g. `boxcox`, `impute`, `diff`) are chained in parallel: `groupby` is only called once.
    By contrast, with eager transforms, operations series-by-series is called in sequence: `groupby-aggregate` is called per transform.

## Global Forecasting

Every `forecaster` exposes a scikit-learn `fit` and `predict` API.
The `fit` method takes `y` and `X` (optional).
The `predict` method takes the forecast horizon `fh: int`, frequency alias `freq: str`, and `X` (optional).

!!! info "Supported Frequency Aliases"

    - 1s (1 second)
    - 1m (1 minute)
    - 30m (30 minute)
    - 1h (1 hour)
    - 1d (1 day)
    - 1w (1 week)
    - 1mo (1 calendar month)
    - 3mo (1 calendar quarter)
    - 1y (1 calendar year)
    - 1i (1 index count)


```python
from functime.forecasting import linear_model
from functime.metrics import mase

# Fit
forecaster = linear_model(lags=24, freq="1mo")
forecaster.fit(y=y_train)

# Predict
y_pred = forecaster.predict(fh=3)

# Score
scores = mase(y_true=y_test, y_pred=y_pred, y_train=y_train)
```

!!! question "Global vs Local Forecasting"

    **`functime` only supports global forecasters.**
    Global forecasters fit and predict a collection of time series using a single model.
    Local forecasters (e.g. ARIMA, ETS, Theta) fit and predict one series per model.
    Example collections of time series, which are also known as panel data, include:

    - Sales across product in a retail store
    - Churn rates across customer segments
    - Sensor data across devices in a factory
    - Delivery times across trucks in a logistics fleet

    Global forecasters, trained on a collection of similar time series, consistently outperform local forecasters.[^1]
    Most notably, all top 50 competitors in the M5 Forecasting Competition used a global LightGBM forecasting model.[^2]

    [^1]: Montero-Manso, P., & Hyndman, R. J. (2021). Principles and algorithms for forecasting groups of time series: Locality and globality. International Journal of Forecasting, 37(4), 1632-1653.

    [^2]: Makridakis, S., Spiliotis, E., & Assimakopoulos, V. (2022). M5 accuracy competition: Results, findings, and conclusions. International Journal of Forecasting.

!!! tip "Save 100x in Cloud spend"

    Local forecasting is expensive and slow.
    To productionize forecasts at scale (>1,000 series), local models have no choice but distributed computing.
    Every fit-predict call per local model per series are executed in parallel across the distributed cluster.
    Running a distributed cluster, however, is a significant cost and time sink for any data team.

    **`functime` believes that the vast majority of businesses do not need distributed computing to produce high-quality forecasts**.
    Every `forecaster`, `transformer`, `splitter`, and `metric` in `functime` operates globally across collections of time series.
    We rewrote every time series operation in `polars` for blazing fast multi-threaded parallelism.

    Stop using Databricks to scale your forecasts. Use `functime`.

## Exogenous Regressors

Every forecaster in `functime` supports exogenous regressors.

```python
from functime.forecasting import linear_model

forecaster = linear_model(lags=24, fit_intercept=False, freq="1mo")
forecaster.fit(y=y_train, X=X_train)
y_pred = forecaster.predict(fh=3, X=X_test)
```

## Seasonality

### Indicators

To model seasonality effects in global forecasting, we recommend using one-hot encoded features of datetime and calendar effects:

  - minute: 1, 2, ..., 60 (in a day)
  - hour: 1, 2, ..., 24 (in a day)
  - day: 1, 2, ..., 31 (in a month)
  - weekday: 1, 2, ..., 7 (in a week)
  - week: 1, 2,..., 52 (in a year)
  - quarter: 1, 2, ..., 4 (in a year)
  - year: 1999, 2000, ..., 2023 (any year)

```python
from functime.feature_extraction import add_calendar_effects

X_new = X.pipe(add_calendar_effects(["month"])).collect()
```

### Holidays / Special Events

`functime` has a wrapper function around the [`holidays`](https://pypi.org/project/holidays/) Python package to generate dummy variables for special events.

```python
from functime.feature_extraction import add_holiday_effects

north_america_holidays = add_holiday_effects(
    country_codes=["US", "CA"],
    freq="1mo"
)
X_new = X.pipe(north_america_holidays).collect()
```

### Fourier

Coming soon.

## Forecast Strategies

`functime` supports three forecast strategies: `recursive`, `direct` multi-step, and a simple ensemble of both `recursive` and `direct`.

```python
from functime.forecasting import linear_model

# Recursive (Default)
recursive_model = linear_model(strategy="recursive")
y_pred_rec = recursive_model(y_train, fh)

# Direct
max_horizons = 12  # Number of direct models
direct_model = = linear_model(strategy="direct",max_horizons=max_horizons, freq="1mo")
y_pred_dir = recursive_model(y_train, fh)

# Ensemble
ensemble_model = linear_model(strategy="ensemble", max_horizons=max_horizons, freq="1mo")
y_pred_ens = ensemble_model(y=y_train, fh=3)
```
where `max_horizons` is the number of models specific to each forecast horizon.
For example, if `max_horizons = 12`, then twelve forecasters are fitted in total: the 1-step ahead forecast, the 2-steps ahead forecast, the 3-steps ahead forecast, ..., and the final 12-steps ahead forecast.

## Censored Forecasts

Most real-world datasets in e-commerce and logistics contain zeros in the target variable: e.g. periods with no sales. To address this problem, `functime` implements the `censored_model` forecaster, which trains a binary classifier and two forecasters. The binary classifier predicts the probability that a forecast falls above or below a certain threshold (e.g. zero). The final forecast is a weighted average of the above and below threshold forecasters.

```python
from functime.forecasting import censored_model

# Load the M5 competition Walmart dataset
y_train = pl.read_parquet("data/m5_y_train.parquet")
X_train = pl.read_parquet("data/m5_X_train.parquet")

# Fit-predict given threshold = 0.0
y_pred = censored_model(lags=3, threshold=0.0, freq="1d")(
    y=y_train, X=X_train, fh=fh, X_future=X_test
)
```

!!! tip "Custom Classfier and Regressors"

    By default, `censored_model` uses sklearn's `HistGradientBoostingClassifier` and `HistGradientBoostingRegressor`.
    To use your own classifier and regressor, implement a function that takes `X` and `y` numpy arrays and returns a fitted sklearn-compatible classifier and regressor.

    ```python
    from sklearn.neural_network import MLPRegressor
    from sklearn.ensemble import RandomForestClassifier

    def regress(X: np.ndarray, y: np.ndarray):
        estimator = MLPRegressor()
        estimator.fit(X=_X_to_numpy(X), y=_y_to_numpy(y))
        return estimator


    def classify(X: np.ndarray, y: np.ndarray):
        estimator = RandomForestClassifier()
        estimator.fit(X=_X_to_numpy(X), y=_y_to_numpy(y))
        return estimator


    # Censored model with custom classifier and regressor
    forecaster = censored_model(
        lags=3,
        threshold=0.0,
        freq="1d",
        classify=classify,
        regress=regress
    )
    y_pred = forecaster(y=y_train, X=X_train, fh=fh, X_future=X_test)
    ```

## AutoML

Forecasters in [auto_forecasting](http://localhost:8000/ref/auto-forecasting/) automatically tune the number of lagged regressors and the model's hyperparameters (e.g. `alpha` for `Lasso`). Cross-validation, lags tuning, and model parameters tuning are performed simultaneously for maximum efficiency.

### Optimal Lag Length

`auto_{model}` forecasters automatically select the optimal number of lags via cross-validation.
These forecasters conduct a search over possible models within `min_lags` and `max_lags`.
The best model is the model with the lowest average RMSE (root mean squared error) across splits.

```python
from functime.forecasting import auto_linear_model

# Fit then predict
forecaster = auto_linear_model(min_lags=20, max_lags=24, freq="1mo")
forecaster.fit(y=y_train, X=X_train)
y_pred = forecaster.predict(fh=3, X=X_test)

# Fit and predict
y_pred = auto_linear_model(min_lags=20, max_lags=24, freq="1mo")(
    y=y_train,
    X=X_train,
    X_future=X_test,
    fh=3
)
```

### Hyperparameter Tuning

`auto_{model}` forecasters automatically select the optimal number of lags via cross-validation.
These forecasters conduct a search over possible models within `min_lags` and `max_lags`.
The best model is the model with the lowest average RMSE (root mean squared error) across splits.

!!! tip "Sane Hyperparameter Defaults"

    Sane defaults are used if `search_space` or `points_to_evaluate` are left as `None`.
    `functime` specify default hyperparameters search spaces according to best-practices from industry, top Kaggle solutions, and research.

`functime` uses [`FLAML`](https://microsoft.github.io/FLAML/docs/getting-started) under the hood to conduct hyperparameter tuning.

```python
from flaml import tune
from functime.forecasting import auto_lightgbm

# Specify search space, initial conditions, and time budget
search_space = {
    "reg_alpha": tune.loguniform(1e-08, 10.0),
    "reg_lambda": tune.loguniform(1e-08, 10.0),
    "num_leaves": tune.randint(
        2, 2**max_depth if max_depth > 0 else 2**DEFAULT_TREE_DEPTH
    ),
    "colsample_bytree": tune.uniform(0.4, 1.0),
    "subsample": tune.uniform(0.4, 1.0),
    "subsample_freq": tune.randint(1, 7),
    "min_child_samples": tune.qlograndint(5, 100, 5),
}
points_to_evaluate = [
    {
        "num_leaves": 31,
        "colsample_bytree": 1.0,
        "subsample": 1.0,
        "min_child_samples": 20,
    }
]
time_budget = 420

# Fit model
forecaster = auto_lightgbm(
    freq="1mo',
    min_lags=20,
    max_lags=24,
    time_budget=time_budget,
    search_space=search_space,
    points_to_evaluate=points_to_evaluate
)
forecaster.fit(y=y_train)

# Get best lags and model hyperparameters
best_params = forecaster.best_params
```

## Backtesting

Every `forecaster` and `auto_forecaster` has a `backtest` method.
`functime` supports both [`expanding_window_split`](https://docs.functime.ai/ref/cross-validation/#functime.cross_validation.expanding_window_split)
and [`sliding_window_split`](https://docs.functime.ai/ref/cross-validation/#functime.cross_validation.sliding_window_split) for backtesting and cross-validation.

```python
from functime.forecasting import linear_model

forecaster = linear_model(lags=24, fit_intercept=False, freq="1mo")
y_preds, y_residuals forecaster.backtest(
    y=y_train,
    X=X_train,
    test_size=6,
    step_size=1,
    n_splits=3,
    window_size=1,  # Only applicable if `strategy` equals "sliding"
    strategy="expanding",
)
```

## Probablistic Forecasts

`functime` supports two methods for generating prediction intervals.

### Quantile Regression

Supported by `LightGBM`, `XGBoost`, and `Catboost` forecasters and their AutoML equivalents.

```python
from functime.forecasting import auto_lightgbm

# Forecasts at 10th and 90th percentile
y_pred_10 = auto_lightgbm(alpha=0.1, freq="1d")(y=y_train, fh=28)
y_pred_90 = auto_lightgbm(alpha=0.9, freq="1d")(y=y_train, fh=28)
```

### Conformal Prediction

`functime` currently supports batch prediction intervals (EnbPI) from the paper [Conformal prediction interval for dynamic time-series](https://arxiv.org/abs/2010.09107)

```python
from functime.conformal import conformalize
from functime.forecasting import linear_model

forecaster = linear_model(lags=24, fit_intercept=False, freq="1mo")
y_preds, y_residuals forecaster.backtest(y=y_train, X=X_train)
# Take the mean prediction across backtest windows per entity
y_pred = pl.concat(
    [
        y_pred,
        y_preds.groupby(y_pred.columns[:2]).agg(
            pl.col(y_pred.columns[-1])
            .median()
            .cast(y_pred.schema[y_pred.columns[-1]])
        ),
    ]
)
# Forecasts at 10th and 90th percentile
y_pred_quantiles = conformalize(y_pred, y_resids, alphas=[0.1, 0.9])
```
