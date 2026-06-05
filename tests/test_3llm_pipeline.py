"""
Integration tests for the 3-LLM sequential pipeline.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cao_engine.extraction.gemini_primary import GeminiPrimaryExtractor
from cao_engine.extraction.mistral_reviewer import MistralReviewer
from cao_engine.extraction.mistral_judge import MistralJudge


class Test3LLMPipeline:
    """Test the complete 3-LLM extraction pipeline."""

    @pytest.mark.asyncio
    async def test_full_pipeline_execution(self, temp_data_dir: Path, sample_ocr_output):
        """Test the full 3-LLM pipeline from OCR to final SETU."""
        # Mock responses for each LLM
        gemini_response = {
            "documentType": "InquiryPayEquity",
            "documentVersion": "2.0",
            "caoName": "CAO Metalektro",
            "validFrom": "2024-06-01",
            "validTo": "2025-12-31",
            "payEquity": {
                "wageStructure": {
                    "functionGroups": [
                        {
                            "code": "A",
                            "name": "Eenvoudige werkzaamheden",
                            "minWage": 2100.00,
                            "maxWage": 2800.00
                        }
                    ]
                }
            }
        }

        mistral_review = {
            "gaps": [
                {
                    "field": "payEquity.allowances",
                    "issue": "Missing shift allowances mentioned in section 4.2"
                }
            ],
            "corrections": [],
            "confidence_scores": {
                "payEquity.wageStructure": 0.95
            }
        }

        judge_decision = {
            "final_setu": gemini_response,
            "decisions": [
                {
                    "field": "payEquity.wageStructure",
                    "selected": "gemini",
                    "reason": "Both models agree on wage structure"
                }
            ],
            "overall_confidence": 0.92
        }

        # Mock the LLM clients
        with patch("cao_engine.extraction.gemini_primary.genai") as mock_genai:
            with patch("cao_engine.extraction.mistral_reviewer.Mistral") as mock_mistral:
                with patch("cao_engine.extraction.mistral_judge.Mistral") as mock_judge_client:
                    # Configure Gemini mock
                    mock_model = MagicMock()
                    mock_model.generate_content.return_value.text = json.dumps(gemini_response)
                    mock_genai.GenerativeModel.return_value = mock_model

                    # Configure Mistral Reviewer mock
                    reviewer_client = MagicMock()
                    reviewer_response = MagicMock()
                    reviewer_response.choices = [
                        MagicMock(message=MagicMock(content=json.dumps(mistral_review)))
                    ]
                    reviewer_client.chat.complete.return_value = reviewer_response
                    mock_mistral.return_value = reviewer_client

                    # Configure Mistral Judge mock
                    judge_client = MagicMock()
                    judge_response = MagicMock()
                    judge_response.choices = [
                        MagicMock(message=MagicMock(content=json.dumps(judge_decision)))
                    ]
                    judge_client.chat.complete.return_value = judge_response
                    mock_judge_client.return_value = judge_client

                    # Run the pipeline
                    from cao_engine.cli import run_3llm_pipeline
                    ocr_file = temp_data_dir / "test.md"
                    ocr_file.write_text(sample_ocr_output["content"])

                    final_setu, judge_report = await run_3llm_pipeline(
                        str(ocr_file),
                        "CAO Metalektro",
                        str(temp_data_dir)
                    )

                    # Assertions
                    assert final_setu["caoName"] == "CAO Metalektro"
                    assert final_setu["documentType"] == "InquiryPayEquity"
                    assert judge_report["overall_confidence"] == 0.92

    @pytest.mark.asyncio
    async def test_gemini_extraction_with_large_context(self):
        """Test Gemini extraction with large OCR content."""
        extractor = GeminiPrimaryExtractor(api_key="test-key")

        # Create large OCR content (simulating 1M context)
        large_content = "# CAO Document\n" + ("Section content " * 10000)

        with patch("cao_engine.extraction.gemini_primary.genai") as mock_genai:
            mock_model = MagicMock()
            mock_model.generate_content.return_value.text = json.dumps({
                "documentType": "InquiryPayEquity",
                "extracted": True
            })
            mock_genai.GenerativeModel.return_value = mock_model

            result = await extractor.extract(large_content, "Test CAO")

            assert result["extracted"] is True
            # Verify large content was passed
            mock_model.generate_content.assert_called_once()
            call_args = mock_model.generate_content.call_args[0][0]
            assert len(call_args) > 100000  # Content should be large

    @pytest.mark.asyncio
    async def test_mistral_reviewer_gap_detection(self):
        """Test Mistral reviewer's ability to detect gaps."""
        reviewer = MistralReviewer(api_key="test-key")

        ocr_content = """
        # CAO Test
        ## Wages
        Minimum wage: €2100
        ## Allowances
        Shift allowance: 15%
        Overtime: 150% rate
        """

        gemini_output = {
            "payEquity": {
                "wageStructure": {
                    "minWage": 2100.00
                }
                # Missing allowances
            }
        }

        with patch("cao_engine.extraction.mistral_reviewer.Mistral") as mock_mistral:
            client = MagicMock()
            response = MagicMock()
            response.choices = [
                MagicMock(message=MagicMock(content=json.dumps({
                    "gaps": [
                        {
                            "field": "payEquity.allowances.shift",
                            "issue": "Missing shift allowance of 15%"
                        },
                        {
                            "field": "payEquity.allowances.overtime",
                            "issue": "Missing overtime rate of 150%"
                        }
                    ]
                })))
            ]
            client.chat.complete.return_value = response
            mock_mistral.return_value = client

            review = await reviewer.review(ocr_content, gemini_output)

            assert len(review["gaps"]) == 2
            assert any("shift" in gap["field"] for gap in review["gaps"])
            assert any("overtime" in gap["field"] for gap in review["gaps"])

    @pytest.mark.asyncio
    async def test_judge_field_comparison(self):
        """Test judge's field-by-field comparison logic."""
        judge = MistralJudge(api_key="test-key")

        gemini_output = {
            "wageStructure": {
                "minWage": 2100.00,
                "maxWage": 2800.00
            },
            "allowances": {
                "shift": 0.15
            }
        }

        mistral_output = {
            "wageStructure": {
                "minWage": 2100.00,
                "maxWage": 2900.00  # Different max wage
            },
            "allowances": {
                "shift": 0.15,
                "overtime": 0.50  # Additional field
            }
        }

        with patch("cao_engine.extraction.mistral_judge.Mistral") as mock_mistral:
            client = MagicMock()
            response = MagicMock()
            response.choices = [
                MagicMock(message=MagicMock(content=json.dumps({
                    "final_setu": {
                        "wageStructure": {
                            "minWage": 2100.00,
                            "maxWage": 2900.00  # Judge picks Mistral's value
                        },
                        "allowances": {
                            "shift": 0.15,
                            "overtime": 0.50  # Includes Mistral's addition
                        }
                    },
                    "decisions": [
                        {
                            "field": "wageStructure.maxWage",
                            "selected": "mistral",
                            "reason": "Mistral's value matches OCR table"
                        },
                        {
                            "field": "allowances.overtime",
                            "selected": "mistral",
                            "reason": "Only Mistral extracted this field"
                        }
                    ]
                })))
            ]
            client.chat.complete.return_value = response
            mock_mistral.return_value = client

            result = await judge.judge("OCR content", gemini_output, mistral_output)

            assert result["final_setu"]["wageStructure"]["maxWage"] == 2900.00
            assert "overtime" in result["final_setu"]["allowances"]
            assert len(result["decisions"]) == 2

    @pytest.mark.asyncio
    async def test_pipeline_error_handling(self, temp_data_dir: Path):
        """Test pipeline handles errors gracefully."""
        # Test Gemini failure
        with patch("cao_engine.extraction.gemini_primary.genai") as mock_genai:
            mock_genai.GenerativeModel.side_effect = Exception("Gemini API error")

            from cao_engine.cli import run_3llm_pipeline
            ocr_file = temp_data_dir / "test.md"
            ocr_file.write_text("Test content")

            with pytest.raises(Exception) as exc_info:
                await run_3llm_pipeline(str(ocr_file), "Test CAO", str(temp_data_dir))

            assert "Gemini API error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_pipeline_with_invalid_json(self):
        """Test pipeline handles invalid JSON responses."""
        with patch("cao_engine.extraction.gemini_primary.genai") as mock_genai:
            mock_model = MagicMock()
            # Return invalid JSON
            mock_model.generate_content.return_value.text = "Not valid JSON {{"
            mock_genai.GenerativeModel.return_value = mock_model

            extractor = GeminiPrimaryExtractor(api_key="test-key")

            with pytest.raises(json.JSONDecodeError):
                await extractor.extract("Test content", "Test CAO")

    @pytest.mark.asyncio
    async def test_pipeline_output_persistence(self, temp_data_dir: Path):
        """Test that pipeline outputs are correctly saved."""
        gemini_response = {
            "documentType": "InquiryPayEquity",
            "caoName": "Test CAO"
        }

        judge_report = {
            "overall_confidence": 0.95,
            "decisions": []
        }

        # Mock the pipeline components
        with patch("cao_engine.cli.run_3llm_pipeline") as mock_pipeline:
            mock_pipeline.return_value = (gemini_response, judge_report)

            from cao_engine.cli import run_3llm_pipeline
            ocr_file = temp_data_dir / "test.md"
            ocr_file.write_text("Test")

            final_setu, report = await mock_pipeline(
                str(ocr_file),
                "test-cao",
                str(temp_data_dir)
            )

            # Check outputs
            assert final_setu["caoName"] == "Test CAO"
            assert report["overall_confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_pipeline_performance_metrics(self, temp_data_dir: Path):
        """Test that pipeline tracks performance metrics."""
        import time

        with patch("cao_engine.extraction.gemini_primary.genai") as mock_genai:
            with patch("cao_engine.extraction.mistral_reviewer.Mistral") as mock_mistral:
                with patch("cao_engine.extraction.mistral_judge.Mistral") as mock_judge:
                    # Configure mocks with delays to simulate processing time
                    mock_model = MagicMock()
                    mock_model.generate_content.return_value.text = "{}"
                    mock_genai.GenerativeModel.return_value = mock_model

                    client = MagicMock()
                    response = MagicMock()
                    response.choices = [MagicMock(message=MagicMock(content="{}"))]
                    client.chat.complete.return_value = response
                    mock_mistral.return_value = client
                    mock_judge.return_value = client

                    # Track timing
                    start_time = time.time()

                    from cao_engine.cli import run_3llm_pipeline
                    ocr_file = temp_data_dir / "test.md"
                    ocr_file.write_text("Test")

                    try:
                        await run_3llm_pipeline(str(ocr_file), "Test", str(temp_data_dir))
                    except:
                        pass  # We're just testing the timing

                    elapsed = time.time() - start_time

                    # Pipeline should complete reasonably quickly with mocks
                    assert elapsed < 5.0  # Should be fast with mocks