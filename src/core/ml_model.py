from sklearn.ensemble import RandomForestClassifier
import numpy as np

class MLSignalEnhancer:
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
    
    def prepare_features(self, df):
        """Buat fitur dari indikator"""
        df = df.copy()
        df['return_1h'] = df['close'].pct_change(1)
        df['return_4h'] = df['close'].pct_change(4)
        df['return_24h'] = df['close'].pct_change(24)
        df['volatility'] = df['close'].rolling(24).std()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # Target: harga naik >1% dalam 4 jam ke depan?
        df['target'] = (df['close'].shift(-4) > df['close'] * 1.01).astype(int)
        
        features = ['rsi', 'macd_histogram', 'return_1h', 'return_4h', 
                    'volatility', 'volume_ratio', 'ema_9', 'ema_21']
        
        return df[features].dropna(), df['target'].dropna()
    
    def train(self, df):
        X, y = self.prepare_features(df)
        # Align indices
        common_idx = X.index.intersection(y.index)
        X, y = X.loc[common_idx], y.loc[common_idx]
        
        self.model.fit(X, y)
        print(f"✅ Model trained. Accuracy: {self.model.score(X, y):.2%}")
    
    def predict(self, df):
        X, _ = self.prepare_features(df)
        if len(X) > 0:
            prob = self.model.predict_proba(X.iloc[[-1]])[0]
            return {'up_probability': prob[1], 'down_probability': prob[0]}
        return None
