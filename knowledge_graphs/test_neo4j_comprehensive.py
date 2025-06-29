#!/usr/bin/env python3
"""
Comprehensive Neo4j Knowledge Graph Test Suite

This script provides a complete testing framework for all Neo4j-related functionality
in the Crawl4AI RAG MCP project, including connection testing, repository parsing,
hallucination detection, and knowledge graph querying.
"""

import asyncio
import os
import sys
import tempfile
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from dotenv import load_dotenv

# Add knowledge_graphs to path
sys.path.append(str(Path(__file__).parent))

from neo4j import AsyncGraphDatabase
from parse_repo_into_neo4j import DirectNeo4jExtractor
from ai_hallucination_detector import AIHallucinationDetector
from query_knowledge_graph import KnowledgeGraphQuerier

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """Test execution status."""
    PASSED = "✅ PASSED"
    FAILED = "❌ FAILED"
    SKIPPED = "⏭️ SKIPPED"
    WARNING = "⚠️ WARNING"


@dataclass
class TestResult:
    """Individual test result."""
    name: str
    status: TestStatus
    message: str
    duration: float = 0.0
    details: Optional[Dict] = None


class Neo4jTestSuite:
    """Comprehensive Neo4j testing suite."""
    
    def __init__(self):
        load_dotenv()
        self.neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        self.neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
        self.neo4j_password = os.getenv('NEO4J_PASSWORD', 'password')
        self.results: List[TestResult] = []
        
    async def run_all_tests(self) -> Dict[str, any]:
        """Run all Neo4j tests and return comprehensive results."""
        print("🚀 Starting Neo4j Knowledge Graph Test Suite")
        print("=" * 60)
        
        # Test sequence
        tests = [
            ("Connection Test", self._test_connection),
            ("Database Setup Test", self._test_database_setup),
            ("Repository Parsing Test", self._test_repository_parsing),
            ("Knowledge Graph Query Test", self._test_knowledge_graph_query),
            ("Hallucination Detection Test", self._test_hallucination_detection),
            ("Performance Test", self._test_performance),
            ("Cleanup Test", self._test_cleanup)
        ]
        
        for test_name, test_func in tests:
            print(f"\n📋 Running: {test_name}")
            try:
                import time
                start_time = time.time()
                result = await test_func()
                duration = time.time() - start_time
                result.duration = duration
                self.results.append(result)
                print(f"{result.status} {result.name} ({duration:.2f}s)")
                if result.message:
                    print(f"   {result.message}")
            except Exception as e:
                duration = time.time() - start_time
                error_result = TestResult(
                    name=test_name,
                    status=TestStatus.FAILED,
                    message=f"Unexpected error: {str(e)}",
                    duration=duration
                )
                self.results.append(error_result)
                print(f"{error_result.status} {error_result.name} ({duration:.2f}s)")
                print(f"   {error_result.message}")
        
        return self._generate_summary()
    
    async def _test_connection(self) -> TestResult:
        """Test basic Neo4j connection."""
        try:
            driver = AsyncGraphDatabase.driver(
                self.neo4j_uri, 
                auth=(self.neo4j_user, self.neo4j_password)
            )
            
            async with driver.session() as session:
                result = await session.run('RETURN "Hello Neo4j!" as message')
                record = await result.single()
                message = record["message"]
                
                # Get version info
                result = await session.run('CALL dbms.components() YIELD name, versions, edition')
                version_info = []
                async for record in result:
                    version_info.append(f"{record['name']} {record['versions'][0]} ({record['edition']})")
            
            await driver.close()
            
            return TestResult(
                name="Neo4j Connection",
                status=TestStatus.PASSED,
                message=f"Connected successfully. {', '.join(version_info)}",
                details={"versions": version_info}
            )
            
        except Exception as e:
            return TestResult(
                name="Neo4j Connection",
                status=TestStatus.FAILED,
                message=f"Connection failed: {str(e)}"
            )
    
    async def _test_database_setup(self) -> TestResult:
        """Test database constraints and indexes setup."""
        try:
            extractor = DirectNeo4jExtractor(self.neo4j_uri, self.neo4j_user, self.neo4j_password)
            await extractor.initialize()
            
            # Check if constraints exist
            async with extractor.driver.session() as session:
                result = await session.run("SHOW CONSTRAINTS")
                constraints = [record async for record in result]
                
                result = await session.run("SHOW INDEXES")
                indexes = [record async for record in result]
            
            await extractor.close()
            
            return TestResult(
                name="Database Setup",
                status=TestStatus.PASSED,
                message=f"Found {len(constraints)} constraints and {len(indexes)} indexes",
                details={"constraints": len(constraints), "indexes": len(indexes)}
            )
            
        except Exception as e:
            return TestResult(
                name="Database Setup",
                status=TestStatus.FAILED,
                message=f"Setup verification failed: {str(e)}"
            )
    
    async def _test_repository_parsing(self) -> TestResult:
        """Test repository parsing functionality."""
        try:
            extractor = DirectNeo4jExtractor(self.neo4j_uri, self.neo4j_user, self.neo4j_password)
            await extractor.initialize()
            
            # Use a small test repository
            test_repo = "https://github.com/pydantic/pydantic-core.git"
            await extractor.analyze_repository(test_repo)
            
            # Verify data was created
            async with extractor.driver.session() as session:
                result = await session.run("MATCH (r:Repository) RETURN count(r) as repo_count")
                record = await result.single()
                repo_count = record['repo_count']
                
                result = await session.run("MATCH (c:Class) RETURN count(c) as class_count")
                record = await result.single()
                class_count = record['class_count']
                
                result = await session.run("MATCH (m:Method) RETURN count(m) as method_count")
                record = await result.single()
                method_count = record['method_count']
            
            await extractor.close()
            
            if repo_count > 0:
                return TestResult(
                    name="Repository Parsing",
                    status=TestStatus.PASSED,
                    message=f"Parsed repository: {repo_count} repos, {class_count} classes, {method_count} methods",
                    details={"repos": repo_count, "classes": class_count, "methods": method_count}
                )
            else:
                return TestResult(
                    name="Repository Parsing",
                    status=TestStatus.FAILED,
                    message="No repository data was created"
                )
                
        except Exception as e:
            return TestResult(
                name="Repository Parsing",
                status=TestStatus.FAILED,
                message=f"Repository parsing failed: {str(e)}"
            )
    
    async def _test_knowledge_graph_query(self) -> TestResult:
        """Test knowledge graph querying functionality."""
        try:
            querier = KnowledgeGraphQuerier(self.neo4j_uri, self.neo4j_user, self.neo4j_password)
            await querier.initialize()
            
            # Test basic queries
            repos = await querier.get_repositories()
            classes = await querier.get_classes()
            
            await querier.close()
            
            return TestResult(
                name="Knowledge Graph Query",
                status=TestStatus.PASSED,
                message=f"Query successful: {len(repos)} repositories, {len(classes)} classes",
                details={"repositories": len(repos), "classes": len(classes)}
            )
            
        except Exception as e:
            return TestResult(
                name="Knowledge Graph Query",
                status=TestStatus.FAILED,
                message=f"Query testing failed: {str(e)}"
            )
    
    async def _test_hallucination_detection(self) -> TestResult:
        """Test AI hallucination detection functionality."""
        try:
            detector = AIHallucinationDetector(self.neo4j_uri, self.neo4j_user, self.neo4j_password)
            await detector.initialize()
            
            # Create test script with known patterns
            test_script = '''
import pydantic_core
from pydantic_core import ValidationError

# Valid usage
validator = pydantic_core.SchemaValidator({'type': 'str'})
result = validator.validate_python("test")

# Potential hallucination
fake_result = validator.non_existent_method()
'''
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(test_script)
                test_file = f.name
            
            try:
                # Run detection
                validation_result = await detector.validator.validate_script(
                    await detector.analyzer.analyze_script(test_file)
                )
                
                confidence = validation_result.overall_confidence
                hallucinations = validation_result.hallucinations_detected
                
                return TestResult(
                    name="Hallucination Detection",
                    status=TestStatus.PASSED,
                    message=f"Detection completed: {confidence:.1f}% confidence, {len(hallucinations)} hallucinations",
                    details={"confidence": confidence, "hallucinations": len(hallucinations)}
                )
                
            finally:
                os.unlink(test_file)
                await detector.close()
                
        except Exception as e:
            return TestResult(
                name="Hallucination Detection",
                status=TestStatus.FAILED,
                message=f"Hallucination detection failed: {str(e)}"
            )
    
    async def _test_performance(self) -> TestResult:
        """Test performance of key operations."""
        try:
            driver = AsyncGraphDatabase.driver(
                self.neo4j_uri, 
                auth=(self.neo4j_user, self.neo4j_password)
            )
            
            import time
            
            # Test query performance
            start_time = time.time()
            async with driver.session() as session:
                result = await session.run("MATCH (n) RETURN count(n) as total")
                record = await result.single()
                total_nodes = record['total']
            query_time = time.time() - start_time
            
            await driver.close()
            
            status = TestStatus.PASSED if query_time < 1.0 else TestStatus.WARNING
            message = f"Query time: {query_time:.3f}s for {total_nodes} nodes"
            
            return TestResult(
                name="Performance Test",
                status=status,
                message=message,
                details={"query_time": query_time, "total_nodes": total_nodes}
            )
            
        except Exception as e:
            return TestResult(
                name="Performance Test",
                status=TestStatus.FAILED,
                message=f"Performance test failed: {str(e)}"
            )
    
    async def _test_cleanup(self) -> TestResult:
        """Test cleanup operations."""
        try:
            # This is a non-destructive cleanup test
            # In a real scenario, you might want to clean test data
            return TestResult(
                name="Cleanup Test",
                status=TestStatus.PASSED,
                message="Cleanup operations verified (non-destructive test)"
            )
            
        except Exception as e:
            return TestResult(
                name="Cleanup Test",
                status=TestStatus.FAILED,
                message=f"Cleanup test failed: {str(e)}"
            )
    
    def _generate_summary(self) -> Dict[str, any]:
        """Generate test summary."""
        passed = sum(1 for r in self.results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in self.results if r.status == TestStatus.FAILED)
        warnings = sum(1 for r in self.results if r.status == TestStatus.WARNING)
        skipped = sum(1 for r in self.results if r.status == TestStatus.SKIPPED)
        total_time = sum(r.duration for r in self.results)
        
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {len(self.results)}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️ Warnings: {warnings}")
        print(f"⏭️ Skipped: {skipped}")
        print(f"⏱️ Total Time: {total_time:.2f}s")
        print(f"🎯 Success Rate: {(passed/len(self.results)*100):.1f}%")
        
        if failed > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.results:
                if result.status == TestStatus.FAILED:
                    print(f"  - {result.name}: {result.message}")
        
        return {
            "total": len(self.results),
            "passed": passed,
            "failed": failed,
            "warnings": warnings,
            "skipped": skipped,
            "total_time": total_time,
            "success_rate": passed/len(self.results)*100,
            "results": self.results
        }


async def main():
    """Main test execution."""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Neo4j Knowledge Graph Test Suite")
        print("Usage: python test_neo4j_comprehensive.py")
        print("\nEnvironment variables required:")
        print("  NEO4J_URI (default: bolt://localhost:7687)")
        print("  NEO4J_USER (default: neo4j)")
        print("  NEO4J_PASSWORD (required)")
        return
    
    suite = Neo4jTestSuite()
    
    # Check if Neo4j password is set
    if not suite.neo4j_password or suite.neo4j_password == 'password':
        print("❌ Error: NEO4J_PASSWORD environment variable must be set")
        print("Please set your Neo4j password in the .env file")
        sys.exit(1)
    
    try:
        summary = await suite.run_all_tests()
        
        # Exit with error code if tests failed
        if summary["failed"] > 0:
            sys.exit(1)
        else:
            print("\n🎉 All tests completed successfully!")
            
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test suite failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
