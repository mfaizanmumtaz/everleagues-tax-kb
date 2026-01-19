/**
 * US State Name to Code Mapping
 * Used to convert frontend full state names to backend state codes
 */

export const STATE_NAME_TO_CODE: Record<string, string> = {
    "Alabama": "AL",
    "Alaska": "AK",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "Florida": "FL",
    "Georgia": "GA",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virginia": "VA",
    "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY",
    "District of Columbia": "DC",
    "Puerto Rico": "PR",
    "U.S. Virgin Islands": "VI",
    "Guam": "GU",
}

export const STATE_CODE_TO_NAME: Record<string, string> = Object.fromEntries(
    Object.entries(STATE_NAME_TO_CODE).map(([name, code]) => [code, name])
)

/**
 * Convert state name to code
 * @param stateName Full state name (e.g., "California")
 * @returns State code (e.g., "CA") or undefined if not found
 */
export function getStateCode(stateName: string): string | undefined {
    return STATE_NAME_TO_CODE[stateName]
}

/**
 * Convert state code to name
 * @param stateCode State code (e.g., "CA")
 * @returns Full state name (e.g., "California") or undefined if not found
 */
export function getStateName(stateCode: string): string | undefined {
    return STATE_CODE_TO_NAME[stateCode]
}
