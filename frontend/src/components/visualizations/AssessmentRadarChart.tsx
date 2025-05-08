import React from 'react';
import { ResponsiveRadar } from '@nivo/radar';

// Define the expected data structure for a single data point in the radar chart
interface RadarDataPoint {
  criteria: string; // e.g., 'Novelty', 'Feasibility'
  score: number;
}

interface AssessmentRadarChartProps {
  data: RadarDataPoint[];
  // Add other Nivo Radar props as needed for customization
  maxValue?: number;
  // Example: Pass colors or theme properties
}

const AssessmentRadarChart: React.FC<AssessmentRadarChartProps> = ({ data, maxValue = 1 }) => {
  if (!data || data.length === 0) {
    return <div>No assessment data available for radar chart.</div>; // Or a loading state
  }

  // Nivo Radar expects keys to be an array of the numerical value fields
  const keys = ['score'];
  const indexBy = 'criteria';

  return (
    // ResponsiveRadar needs a container with definite height
    <div style={{ height: '400px', width: '100%' }}> 
      <ResponsiveRadar
        data={data}
        keys={keys}
        indexBy={indexBy}
        valueFormat=">-.2f" // Format score to 2 decimal places
        maxValue={maxValue} // Typically 1 or 100 depending on score range
        margin={{ top: 70, right: 80, bottom: 40, left: 80 }}
        borderColor={{ from: 'color' }}
        gridLabelOffset={36}
        dotSize={10}
        dotColor={{ theme: 'background' }}
        dotBorderWidth={2}
        colors={{ scheme: 'nivo' }} // Use a predefined color scheme
        blendMode="multiply"
        motionConfig="wobbly"
        legends={[
          {
            anchor: 'top-left',
            direction: 'column',
            translateX: -50,
            translateY: -40,
            itemWidth: 80,
            itemHeight: 20,
            itemTextColor: '#999',
            symbolSize: 12,
            symbolShape: 'circle',
            effects: [
              {
                on: 'hover',
                style: {
                  itemTextColor: '#000'
                }
              }
            ]
          }
        ]}
        // Add more props for customization (theme, tooltips, etc.)
      />
    </div>
  );
};

export { AssessmentRadarChart };
export type { AssessmentRadarChartProps, RadarDataPoint };
