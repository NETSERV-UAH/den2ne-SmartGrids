% Script para leer un CSV y generar 4 versiones modificadas de la columna R (ohm/km)

% Nombre del archivo de entrada
input_file = 'links_config.csv'; % Cambiar según el nombre real del CSV

% Leer el archivo CSV
opts = detectImportOptions(input_file, 'Delimiter', ',', 'VariableNamesLine', 1);
data = readtable(input_file, opts);

% Verificar que la columna 'R (ohm/km)' existe
col_name = 'R_ohm_km_';
if ~ismember(col_name, data.Properties.VariableNames)
    error('La columna "%s" no se encontró en el archivo.', col_name);
end

% Crear variaciones de R
scales = [1, 0.5, 0.25, 0.125]; 
filenames = {'links_config_100.csv', 'links_config_50.csv', 'links_config_25.csv', 'links_config_12_5.csv'};

for i = 1:length(scales)
    modified_data = data;
    modified_data.(col_name) = modified_data.(col_name) * scales(i);
    writetable(modified_data, filenames{i});
end

disp('Archivos generados correctamente.');
