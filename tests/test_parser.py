import pytest
from unittest.mock import MagicMock
from app.parser import TransactionParser, SOL_MINT

# Helper to create mock solders-like objects
class MockObject:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
    def __str__(self):
        return getattr(self, "address", getattr(self, "mint", "MockObject"))

@pytest.mark.asyncio
async def test_parse_buy_success():
    wallet_addr = "6ghp..."
    
    # Mock Token balances
    post_token = MockObject(
        mint=MockObject(mint="MemeMint123"),
        owner=MockObject(address=wallet_addr),
        ui_token_amount=MockObject(amount="1000000", decimals=6)
    )
    
    mock_meta = MagicMock()
    mock_meta.pre_token_balances = []
    mock_meta.post_token_balances = [post_token]
    mock_meta.pre_balances = [2000000000] # 2 SOL
    mock_meta.post_balances = [1000000000] # 1 SOL (paid 1 SOL)
    
    mock_tx = MagicMock()
    mock_tx.meta = mock_meta
    
    result = await TransactionParser.parse_buy(mock_tx, wallet_addr)
    assert result is not None
    assert "MemeMint123" in str(result["mint"])
    assert result["amount"] == 1.0
    assert result["pay_amount"] == 1.0

@pytest.mark.asyncio
async def test_parse_sell_success():
    wallet_addr = "6ghp..."
    
    # Mock Token balances
    pre_token = MockObject(
        mint=MockObject(mint="MemeMint123"),
        owner=MockObject(address=wallet_addr),
        ui_token_amount=MockObject(amount="1000000", decimals=6)
    )
    
    mock_meta = MagicMock()
    mock_meta.pre_token_balances = [pre_token]
    mock_meta.post_token_balances = []
    mock_meta.pre_balances = [1000000000] # 1 SOL
    mock_meta.post_balances = [2500000000] # 2.5 SOL (received 1.5 SOL)
    
    mock_tx = MagicMock()
    mock_tx.meta = mock_meta
    
    result = await TransactionParser.parse_sell(mock_tx, wallet_addr)
    assert result is not None
    assert "MemeMint123" in str(result["mint"])
    assert result["amount"] == 1.0
    assert result["receive_amount"] == 1.5
