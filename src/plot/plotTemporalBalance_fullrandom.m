%% plotRangeLoads_fullrandom.m
%
%   [+] Autor: David Carrascal <david.carrascal@uah.es> 
%
%   [+] Fecha:  4 Mar 2025
clc
close all
clear varibles

base_path = "../results/ieee123_fullrandom/";
root_folders = dir(fullfile(base_path, "root_*"));
num_roots = length(root_folders);

% Directorio donde se guardarán los resultados combinados
combined_results_path = fullfile(base_path, "global_results");
if ~exist(combined_results_path, 'dir')
    mkdir(combined_results_path);
end

% Directorio donde se guardarán los resultados combinados, los csvs
combined_results_path_csv = fullfile(combined_results_path, "csv");
if ~exist(combined_results_path_csv, 'dir')
    mkdir(combined_results_path_csv);
end

% Inicializar estructura para almacenar los datos promediados
num_deltas = 96; % Asumiendo 96 intervalos de tiempo
num_criteria = 5; % Cantidad de criterios seleccionados

% Matriz para almacenar los datos de todos los roots
data3d_all_roots = zeros(num_criteria, 13, num_deltas, num_roots);

for r = 1:num_roots
    root_path = fullfile(base_path, root_folders(r).name);
    
    for d = 0:num_deltas-1
        file_path = fullfile(root_path, strcat("csv/outdata_d", num2str(d), ".csv"));
        
        if exist(file_path, 'file')
            data_table = readtable(file_path, 'NumHeaderLines', 1);
            data = data_table{:,:};
            data3d_all_roots(:, :, d+1, r) = data(:, :);
        end
    end
end

% Calcular promedio sobre todos los roots
data_avg_all = mean(data3d_all_roots, 4);

% Cabecera 
header = ["criterion", "power_ideal", "abs_ideal", "power_wloss", "abs_wloss", ...
          "power_wlossCap", "abs_wlossCap", "timestamp_ideal", "timestamp_wloss", "timestamp_wlossCap","iteration_ideal","iteration_wloss","iteration_wlossCap"];

% Guardar los datos combinados en archivos CSV
for d = 0:num_deltas-1
    output_file = fullfile(combined_results_path,"csv", strcat("outdata_d", num2str(d), ".csv"));

    writematrix(header, output_file);
    writematrix(squeeze(data_avg_all(:, :, d+1)), output_file, 'WriteMode', 'append');
end

% Ejecutar plotRangeLoads en los resultados combinados
plotTemporalBalance(0, 95, combined_results_path);