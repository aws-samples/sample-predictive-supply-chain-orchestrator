# Chronos-2 Setup Guide

## Windows Long Path Issue

The Chronos-2 installation requires Windows Long Path support to be enabled.

### Enable Long Paths on Windows

**Option 1: Using Registry Editor (Recommended)**

1. Press `Win + R`, type `regedit`, and press Enter
2. Navigate to: `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\FileSystem`
3. Find or create a DWORD value named `LongPathsEnabled`
4. Set its value to `1`
5. Restart your computer

**Option 2: Using PowerShell (Admin)**

```powershell
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

**Option 3: Using Group Policy (Windows Pro/Enterprise)**

1. Press `Win + R`, type `gpedit.msc`, and press Enter
2. Navigate to: Computer Configuration > Administrative Templates > System > Filesystem
3. Enable "Enable Win32 long paths"
4. Restart your computer

### After Enabling Long Paths

Install the required packages:

```bash
pip install 'chronos-forecasting>=2.0' 'pandas[pyarrow]' numpy
```

## Alternative: Use SageMaker Deployment

If you prefer not to modify Windows settings, you can deploy Chronos-2 to Amazon SageMaker:

```python
from sagemaker.jumpstart.model import JumpStartModel

model = JumpStartModel(
    model_id="pytorch-forecasting-chronos-2",
    instance_type="ml.g5.2xlarge",
)
predictor = model.deploy()
```

Then modify the agent to call the SageMaker endpoint instead of loading the model locally.

## Testing Without Chronos-2

For development and testing the agent structure without Chronos-2 installed, the agent will use mock forecasts. This allows you to:

- Test the agent conversation flow
- Verify tool integration
- Test the API endpoints
- Develop the frontend

Once Chronos-2 is installed, the agent will automatically use the real model.

## Verification

After installation, verify Chronos-2 is working:

```python
from chronos import Chronos2Pipeline
import pandas as pd

# Load model
pipeline = Chronos2Pipeline.from_pretrained("amazon/chronos-2", device_map="cpu")

# Test with sample data
df = pd.DataFrame({
    'timestamp': pd.date_range('2024-01-01', periods=100, freq='D'),
    'target': range(100),
    'id': 'test'
})

# Generate forecast
pred_df = pipeline.predict_df(
    df,
    prediction_length=10,
    quantile_levels=[0.5],
    id_column="id",
    timestamp_column="timestamp",
    target="target"
)

print("✅ Chronos-2 is working!")
print(pred_df.head())
```

## Resources

- [Chronos-2 Documentation](https://huggingface.co/amazon/chronos-2)
- [Windows Long Path Support](https://pip.pypa.io/warnings/enable-long-paths)
- [SageMaker Deployment Guide](https://github.com/amazon-science/chronos-forecasting)
