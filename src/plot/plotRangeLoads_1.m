%% plotRangeLoads.m
%
%   [+] Autor: David Carrascal <david.carrascal@uah.es> 
%
%   [+] Fecha:  14 Feb 2025

function plotRangeLoads_1(init, fin, result_path)
    
    % Preparamos la matriz de datos 
    data3d = zeros(4, 10, fin-init+1); % Se reduce a 4 criterios
    
    % Obtenemos los datos de los ficheros csv indicados
    for i = init:fin
        file_path = fullfile(result_path, strcat("csv/outdata_d", num2str(i), ".csv"));
        data_table = readtable(file_path, 'NumHeaderLines', 1);
        
        % Pasamos a matriz y filtramos los criterios
        data = data_table{:,:};
        selected_criteria = [1, 3, 4, 5]; % Se eliminó el criterio de distancia
        data3d(:, :, i-init+1) = data(selected_criteria, :);
    end
    
    % Obtenemos la media y el error estándar
    data_avg = mean(data3d(:, 2:7, :), 3);
    sem = std(data3d(:, 2:7, :), [], 3) / sqrt(fin-init+1);
    
    % Obtenemos la media y el error estándar de los tiempos
    time_avg = mean(data3d(:, 8:10, :), 3);
    sem_time = std(data3d(:, 8:10, :), [], 3) / sqrt(fin-init+1);
    
    % Pintamos la figura de balance global de potencias
    data_power = data_avg(:, [1 3 5]);
    sem_power = sem(:, [1 3 5]);
    
    h = figure();
    set(gcf, 'Position', [100 100 900 700]);
    bar_handle = bar(data_power, 0.6, 'grouped', 'FaceColor', 'flat'); hold on; % Barras más finas
    
    % Error bars
    ngroups = size(data_power, 1);
    nbars = size(data_power, 2);
    groupwidth = min(0.6, nbars/(nbars + 1.5)); % Espaciado entre barras
    
    for i = 1:nbars
        x = bar_handle(i).XEndPoints; % Obtiene las posiciones correctas de las barras
        errorbar(x, data_power(:, i), sem_power(:, i), 'k', 'linestyle', 'none', 'CapSize', 10);
    end
    
    grid on;
    title("Average global power balance", 'FontSize', 16);
    ylabel("Power (kW)");
    legend("Ideal", "Lossy", "Lossy-constrained link capacity", 'Location', 'southoutside', 'NumColumns', 3);
    set(gca, 'XTickLabel', {'Hops', 'Losses', 'Power 0', 'Power 0 + Losses'});
    hold off;
    
    print(h, fullfile(result_path, 'fig/powerBalance_global'), '-dpdf', '-r300');
    
    % Pintamos los tiempos promedios
    h = figure();
    set(gcf, 'Position', [100 100 900 700]);
    bar_handle = bar(time_avg, 0.6, 'grouped', 'FaceColor', 'flat'); hold on;
    
    % Error bars para los tiempos
    for i = 1:nbars
        x = bar_handle(i).XEndPoints; % Obtiene las posiciones correctas de las barras
        errorbar(x, time_avg(:, i), sem_time(:, i), 'k', 'linestyle', 'none', 'CapSize', 10);
    end
    
    grid on;
    title("Average processing times", 'FontSize', 16);
    ylabel("Time (ms)");
    legend("Ideal", "Lossy", "Lossy-constrained link capacity", 'Location', 'southoutside', 'NumColumns', 3);
    set(gca, 'XTickLabel', {'Hops', 'Losses', 'Power 0', 'Power 0 + Losses'});
    hold off;
    
    print(h, fullfile(result_path, 'fig/processingTimes_global'), '-dpdf', '-r300');
end
