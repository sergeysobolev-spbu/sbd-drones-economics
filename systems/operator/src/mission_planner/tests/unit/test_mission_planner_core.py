"""
Unit tests for MissionPlannerCore
"""
import pytest
from datetime import datetime
import time

from systems.operator.src.mission_planner.src.mission_planner_core import (
    MissionPlannerCore,
    MissionStatus,
    ValidationResult,
    Waypoint,
    FlightPlan,
    ValidationIssue,
    SafetyConstraints
)


class TestMissionPlannerCore:
    """Tests for MissionPlannerCore"""
    
    @pytest.fixture
    def core(self):
        """Create MissionPlannerCore instance"""
        return MissionPlannerCore()
    
    @pytest.fixture
    def valid_waypoints(self):
        """Create valid waypoints"""
        return [
            Waypoint(
                latitude=55.7558,
                longitude=37.6173,
                altitude=50.0,
                speed=10.0,
                action="takeoff"
            ),
            Waypoint(
                latitude=55.7600,
                longitude=37.6200,
                altitude=50.0,
                speed=15.0,
                action="photo",
                duration=5.0
            ),
            Waypoint(
                latitude=55.7650,
                longitude=37.6250,
                altitude=50.0,
                speed=15.0
            ),
            Waypoint(
                latitude=55.7558,
                longitude=37.6173,
                altitude=0.0,
                speed=5.0,
                action="land"
            )
        ]
    
    @pytest.fixture
    def emergency_points(self):
        """Create emergency landing points"""
        return [
            Waypoint(
                latitude=55.7580,
                longitude=37.6190,
                altitude=0.0,
                speed=0.0
            ),
            Waypoint(
                latitude=55.7620,
                longitude=37.6220,
                altitude=0.0,
                speed=0.0
            )
        ]
    
    @pytest.fixture
    def valid_flight_plan(self, valid_waypoints, emergency_points):
        """Create valid flight plan"""
        return FlightPlan(
            mission_id="test-mission-001",
            uas_id="uas-001",
            waypoints=valid_waypoints,
            takeoff_time=datetime.now().timestamp() + 3600,  # 1 hour from now
            estimated_duration=600.0,  # 10 minutes
            max_altitude=50.0,
            total_distance=2000.0,
            emergency_landing_points=emergency_points
        )
    
    def test_validate_valid_flight_plan(self, core, valid_flight_plan):
        """Test validation of valid flight plan"""
        result, issues = core.validate_flight_plan(valid_flight_plan)
        
        assert result == ValidationResult.VALID
        assert len(issues) == 0
    
    def test_validate_altitude_exceeded(self, core, valid_flight_plan):
        """Test validation with altitude exceeding limit"""
        # Modify one waypoint to exceed altitude
        valid_flight_plan.waypoints[1].altitude = 150.0  # Exceeds 120m limit
        
        result, issues = core.validate_flight_plan(valid_flight_plan)
        
        assert result == ValidationResult.INVALID
        assert len(issues) > 0
        assert any(issue.issue_type == "altitude_exceeded" for issue in issues)
        assert any(issue.severity == "critical" for issue in issues)
    
    def test_validate_speed_exceeded(self, core, valid_flight_plan):
        """Test validation with speed exceeding limit"""
        # Modify waypoint to exceed speed
        valid_flight_plan.waypoints[1].speed = 25.0  # Exceeds 20m/s limit
        
        result, issues = core.validate_flight_plan(valid_flight_plan)
        
        assert result == ValidationResult.INVALID
        assert len(issues) > 0
        assert any(issue.issue_type == "speed_exceeded" for issue in issues)
    
    def test_validate_no_fly_zone_violation(self, core):
        """Test validation with no-fly zone violation"""
        # Create waypoints that violate no-fly zone
        waypoints = [
            Waypoint(
                latitude=55.7558,  # Near airport no-fly zone
                longitude=37.6173,
                altitude=50.0,
                speed=10.0
            )
        ]
        
        plan = FlightPlan(
            mission_id="test-002",
            uas_id="uas-002",
            waypoints=waypoints,
            takeoff_time=time.time(),
            estimated_duration=300.0,
            max_altitude=50.0,
            total_distance=1000.0,
            emergency_landing_points=[]
        )
        
        result, issues = core.validate_flight_plan(plan)
        
        assert result == ValidationResult.INVALID
        assert any(issue.issue_type == "no_fly_zone_violation" for issue in issues)
    
    def test_validate_no_emergency_points(self, core, valid_waypoints):
        """Test validation without emergency landing points"""
        plan = FlightPlan(
            mission_id="test-003",
            uas_id="uas-003",
            waypoints=valid_waypoints,
            takeoff_time=time.time(),
            estimated_duration=600.0,
            max_altitude=50.0,
            total_distance=2000.0,
            emergency_landing_points=[]  # No emergency points
        )
        
        result, issues = core.validate_flight_plan(plan)
        
        assert result == ValidationResult.INVALID
        assert any(issue.issue_type == "no_emergency_points" for issue in issues)
    
    def test_calculate_flight_parameters(self, core, valid_waypoints):
        """Test flight parameters calculation"""
        params = core.calculate_flight_parameters(valid_waypoints)
        
        assert "total_distance" in params
        assert "estimated_duration" in params
        assert "max_altitude" in params
        assert "average_speed" in params
        assert "waypoint_count" in params
        
        assert params["waypoint_count"] == len(valid_waypoints)
        assert params["max_altitude"] == 50.0
        assert params["total_distance"] > 0
        assert params["estimated_duration"] > 0
    
    def test_mission_conflict_detection(self, core, valid_flight_plan):
        """Test detection of conflicts between missions"""
        # Register first mission
        core.register_active_mission(valid_flight_plan)
        
        # Create conflicting mission (same time and area)
        conflicting_plan = FlightPlan(
            mission_id="test-conflict",
            uas_id="uas-conflict",
            waypoints=valid_flight_plan.waypoints,
            takeoff_time=valid_flight_plan.takeoff_time,
            estimated_duration=valid_flight_plan.estimated_duration,
            max_altitude=valid_flight_plan.max_altitude,
            total_distance=valid_flight_plan.total_distance,
            emergency_landing_points=valid_flight_plan.emergency_landing_points
        )
        
        result, issues = core.validate_flight_plan(conflicting_plan)
        
        assert result == ValidationResult.INVALID
        assert any(issue.issue_type == "mission_conflict" for issue in issues)
        
        # Cleanup
        core.unregister_mission(valid_flight_plan.mission_id)
    
    def test_active_missions_management(self, core, valid_flight_plan):
        """Test active missions registration and unregistration"""
        assert core.get_active_missions_count() == 0
        
        # Register mission
        core.register_active_mission(valid_flight_plan)
        assert core.get_active_missions_count() == 1
        
        # Unregister mission
        core.unregister_mission(valid_flight_plan.mission_id)
        assert core.get_active_missions_count() == 0
    
    def test_distance_calculation(self, core):
        """Test distance calculation between points"""
        # Moscow to Saint Petersburg approximately
        distance = core._calculate_distance(55.7558, 37.6173, 59.9311, 30.3609)
        
        # Should be approximately 635 km
        assert 630000 < distance < 640000
    
    def test_total_distance_calculation(self, core, valid_waypoints):
        """Test total distance calculation for route"""
        total_distance = core._calculate_total_distance(valid_waypoints)
        
        assert total_distance > 0
        # Should be sum of distances between consecutive waypoints
        assert total_distance < 10000  # Less than 10km for test waypoints
    
    def test_flight_duration_estimation(self, core, valid_waypoints):
        """Test flight duration estimation"""
        duration = core._estimate_flight_duration(valid_waypoints)
        
        assert duration > 0
        # Should include travel time and action durations
        assert duration > 5.0  # At least the photo duration
    
    def test_safety_constraints_defaults(self, core):
        """Test default safety constraints"""
        constraints = core.safety_constraints
        
        assert constraints.max_altitude == 120.0
        assert constraints.max_speed == 20.0
        assert constraints.min_battery_reserve == 0.2
        assert constraints.max_wind_speed == 10.0
        assert constraints.min_visibility == 1000.0
        assert constraints.geofence_radius == 1000.0
    
    def test_low_altitude_warning(self, core, valid_flight_plan):
        """Test warning for low altitude"""
        # Set very low altitude
        valid_flight_plan.waypoints[1].altitude = 5.0
        
        result, issues = core.validate_flight_plan(valid_flight_plan)
        
        # Should be warning, not critical
        assert result == ValidationResult.WARNING
        assert any(issue.issue_type == "altitude_too_low" for issue in issues)
        assert any(issue.severity == "warning" for issue in issues)
    
    def test_long_distance_warning(self, core, valid_waypoints, emergency_points):
        """Test warning for long distance flights"""
        # Create waypoints for long distance
        long_waypoints = [
            Waypoint(lat=55.0, lon=37.0, altitude=50.0, speed=15.0),
            Waypoint(lat=55.1, lon=37.1, altitude=50.0, speed=15.0),
            Waypoint(lat=55.2, lon=37.2, altitude=50.0, speed=15.0),
            Waypoint(lat=55.0, lon=37.0, altitude=0.0, speed=5.0)
        ]
        
        plan = FlightPlan(
            mission_id="long-001",
            uas_id="uas-long",
            waypoints=long_waypoints,
            takeoff_time=time.time(),
            estimated_duration=3600.0,
            max_altitude=50.0,
            total_distance=15000.0,  # 15km
            emergency_landing_points=emergency_points
        )
        
        result, issues = core.validate_flight_plan(plan)
        
        # Should have range warning
        assert any(issue.issue_type == "range_exceeded" for issue in issues)
    
    def test_emergency_point_distance_check(self, core, valid_waypoints):
        """Test emergency landing point distance validation"""
        # Create emergency points far from route
        far_emergency_points = [
            Waypoint(lat=56.0, lon=38.0, altitude=0.0, speed=0.0)  # Very far
        ]
        
        plan = FlightPlan(
            mission_id="emergency-test",
            uas_id="uas-emergency",
            waypoints=valid_waypoints,
            takeoff_time=time.time(),
            estimated_duration=600.0,
            max_altitude=50.0,
            total_distance=2000.0,
            emergency_landing_points=far_emergency_points
        )
        
        result, issues = core.validate_flight_plan(plan)
        
        # Should have warnings about emergency points being too far
        assert any(issue.issue_type == "emergency_point_too_far" for issue in issues)