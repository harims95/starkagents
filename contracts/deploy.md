# Deploy VerdictRegistry to StarkNet Sepolia

## Prerequisites

```bash
# Install Scarb (Cairo package manager)
curl --proto '=https' --tlsv1.2 -sSf https://docs.swmansion.com/scarb/install.sh | sh

# Install Starkli (StarkNet CLI)
curl https://get.starkli.sh | sh
starkliup
```

## 1. Build the contract

```bash
cd contracts
scarb build
# Output: target/dev/starkagents_VerdictRegistry.contract_class.json
```

## 2. Set up Starkli account (Sepolia)

```bash
# Create keystore from private key
starkli signer keystore from-key ~/.starkli-wallets/deployer/keystore.json
# Enter your private key when prompted

# Create account descriptor
starkli account fetch \
  YOUR_ACCOUNT_ADDRESS \
  --rpc https://free-rpc.nethermind.io/sepolia-juno \
  --output ~/.starkli-wallets/deployer/account.json
```

## 3. Declare the contract

```bash
starkli declare \
  target/dev/starkagents_VerdictRegistry.contract_class.json \
  --account ~/.starkli-wallets/deployer/account.json \
  --keystore ~/.starkli-wallets/deployer/keystore.json \
  --rpc https://free-rpc.nethermind.io/sepolia-juno \
  --watch

# Save the CLASS HASH from output
```

## 4. Deploy the contract

```bash
starkli deploy \
  CLASS_HASH_FROM_ABOVE \
  YOUR_ACCOUNT_ADDRESS \
  --account ~/.starkli-wallets/deployer/account.json \
  --keystore ~/.starkli-wallets/deployer/keystore.json \
  --rpc https://free-rpc.nethermind.io/sepolia-juno \
  --watch

# Save the CONTRACT ADDRESS from output
```

## 5. Update frontend

In `frontend/index.html`, find `runProving()` and replace the mock tx with:

```javascript
const VERDICT_REGISTRY = "YOUR_CONTRACT_ADDRESS_HERE";
```

## 6. Verify on Starkscan

https://sepolia.starkscan.co/contract/YOUR_CONTRACT_ADDRESS
